#!/usr/bin/env sh
# Emite o certificado TLS inicial do domínio de produção.
#
# Resolve um ovo-e-galinha: o server block :443 referencia
# /etc/letsencrypt/live/$DOMAIN/fullchain.pem, então o nginx não sobe sem certificado — mas
# o certbot precisa do nginx no ar para responder ao desafio HTTP-01. A saída é subir com um
# autoassinado descartável, pedir o real e recarregar.
#
# Rodar UMA vez, na VPS, com o DNS de $DOMAIN já apontando para ela:
#   ./deploy/init-letsencrypt.sh
#   STAGING=1 ./deploy/init-letsencrypt.sh   # ensaio, sem gastar o limite semanal
#
# Depois disso a renovação é automática: o serviço `certbot` roda `renew` de 12h em 12h e o
# `nginx` recarrega de 6h em 6h.

set -eu

cd "$(dirname "$0")/.."

COMPOSE="docker compose -f docker-compose.prod.yml"

if [ ! -f .env ]; then
    echo "ERRO: .env não encontrado na raiz do projeto. Rode: cp .env.production .env" >&2
    exit 1
fi

# Lê uma variável do .env sem dar `source` no arquivo: valores como
# CORS_ORIGINS=["https://..."] quebrariam em sh.
read_env() {
    grep -E "^$1=" .env | head -n1 | cut -d= -f2-
}

DOMAIN="$(read_env DOMAIN)"
EMAIL="$(read_env LETSENCRYPT_EMAIL)"
STAGING="${STAGING:-0}"

if [ -z "$DOMAIN" ]; then
    echo "ERRO: DOMAIN vazio no .env." >&2
    exit 1
fi

if [ -z "$EMAIL" ]; then
    echo "ERRO: LETSENCRYPT_EMAIL vazio no .env — o Let's Encrypt exige um e-mail de" >&2
    echo "      contato para avisar de falha de renovação e expiração." >&2
    exit 1
fi

LIVE_DIR="/etc/letsencrypt/live/$DOMAIN"

echo "==> [1/5] Certificado autoassinado temporário para $DOMAIN"
# Serve só para o nginx conseguir iniciar e atender o desafio na porta 80. Validade de 1 dia
# justamente para não passar por certificado bom se algo falhar no meio do caminho.
$COMPOSE run --rm --entrypoint sh certbot -c "
    mkdir -p '$LIVE_DIR' &&
    openssl req -x509 -nodes -newkey rsa:2048 -days 1 \
        -keyout '$LIVE_DIR/privkey.pem' \
        -out '$LIVE_DIR/fullchain.pem' \
        -subj '/CN=$DOMAIN'
"

echo "==> [2/5] Subindo o nginx (e as dependências)"
$COMPOSE up -d nginx

echo "==> [3/5] Removendo o certificado temporário"
# O certbot se recusa a sobrescrever um lineage que ele não criou, por isso a limpeza vem
# antes do pedido real. O nginx já está carregado em memória e segue servindo o antigo.
$COMPOSE run --rm --entrypoint sh certbot -c "
    rm -rf '$LIVE_DIR' \
           '/etc/letsencrypt/archive/$DOMAIN' \
           '/etc/letsencrypt/renewal/$DOMAIN.conf'
"

echo "==> [4/5] Pedindo o certificado real ao Let's Encrypt"
# STAGING=1 usa o ambiente de teste: o certificado sai inválido no navegador, mas não
# consome o limite de 5 emissões por domínio por semana. Vale para ensaiar o fluxo.
STAGING_ARG=""
if [ "$STAGING" = "1" ]; then
    STAGING_ARG="--staging"
    echo "    (modo STAGING — certificado NÃO será aceito pelo navegador)"
fi

# shellcheck disable=SC2086
$COMPOSE run --rm --entrypoint certbot certbot \
    certonly --webroot --webroot-path=/var/www/certbot \
    $STAGING_ARG \
    --email "$EMAIL" --agree-tos --no-eff-email \
    -d "$DOMAIN" \
    --non-interactive

echo "==> [5/5] Recarregando o nginx com o certificado real"
$COMPOSE exec nginx nginx -s reload

echo
echo "OK — https://$DOMAIN"
