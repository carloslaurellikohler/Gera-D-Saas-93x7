import Icon from "./Icon";

interface Props {
  children: string;
}

export default function ErrorBanner({ children }: Props) {
  return (
    <div className="ui-error-banner" role="alert">
      <Icon name="error" size={20} filled color="#A10019" />
      <span>{children}</span>
    </div>
  );
}
