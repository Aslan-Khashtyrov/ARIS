import { Component } from 'react';

export class ErrorBoundary extends Component {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  componentDidUpdate(previousProps) {
    if (this.state.failed && previousProps.resetKey !== this.props.resetKey) {
      this.setState({ failed: false });
    }
  }

  render() {
    if (!this.state.failed) return this.props.children;
    const { t } = this.props;
    return <section className="services-view">
      <div className="panel recovery-card">
        <span className="kicker">{t.recoveryKicker}</span>
        <h2>{t.recoveryTitle}</h2>
        <p>{t.recoveryDescription}</p>
        <button className="action-button" onClick={() => this.setState({ failed: false })}>{t.recoveryRetry}</button>
      </div>
    </section>;
  }
}
