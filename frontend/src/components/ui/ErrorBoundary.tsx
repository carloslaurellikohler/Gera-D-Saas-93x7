import { Component, type ErrorInfo, type ReactNode } from "react";
import ErrorBanner from "./ErrorBanner";

interface Props {
  children: ReactNode;
}

interface State {
  error: Error | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("Erro ao renderizar conteúdo da análise:", error, info.componentStack);
  }

  render() {
    if (this.state.error) {
      return (
        <ErrorBanner>
          Não foi possível exibir esta seção. Os dados desta análise podem estar incompletos ou
          em um formato inesperado.
        </ErrorBanner>
      );
    }
    return this.props.children;
  }
}
