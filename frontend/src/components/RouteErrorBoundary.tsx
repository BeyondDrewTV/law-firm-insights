import React from "react";

interface RouteErrorBoundaryProps {
  children: React.ReactNode;
  title?: string;
}

interface RouteErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  retryKey: number;
}

export default class RouteErrorBoundary extends React.Component<
  RouteErrorBoundaryProps,
  RouteErrorBoundaryState
> {
  state: RouteErrorBoundaryState = {
    hasError: false,
    error: null,
    retryKey: 0,
  };

  static getDerivedStateFromError(error: Error): Partial<RouteErrorBoundaryState> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo): void {
    if (import.meta.env.DEV) {
      console.error("[RouteErrorBoundary] route render error", error, errorInfo);
    }
  }

  private handleRetry = () => {
    this.setState((previous) => ({
      hasError: false,
      error: null,
      retryKey: previous.retryKey + 1,
    }));
  };

  private handleRefresh = () => {
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      return (
        <section className="gov-page">
          <article className="gov-level-2">
            <h1 className="gov-h2 text-neutral-900">
              {this.props.title || "Execution failed to load"}
            </h1>
            <p className="text-sm text-neutral-700">
              Please retry. If it persists, refresh.
            </p>
            <div className="flex flex-wrap gap-2 pt-2">
              <button type="button" className="gov-btn-secondary" onClick={this.handleRetry}>
                Retry
              </button>
              <button type="button" className="gov-btn-secondary" onClick={this.handleRefresh}>
                Refresh page
              </button>
            </div>
            {import.meta.env.DEV && this.state.error ? (
              <details className="mt-2 rounded border border-neutral-300 bg-neutral-50 p-2 text-xs text-neutral-700">
                <summary className="cursor-pointer font-medium text-neutral-800">Error details</summary>
                <pre className="mt-2 whitespace-pre-wrap break-words">{this.state.error.stack || this.state.error.message}</pre>
              </details>
            ) : null}
          </article>
        </section>
      );
    }

    return <React.Fragment key={this.state.retryKey}>{this.props.children}</React.Fragment>;
  }
}
