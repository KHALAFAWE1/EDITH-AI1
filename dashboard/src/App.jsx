import "./App.css";

function Card({ icon, title, text }) {
  return (
    <div className="card">
      <div className="icon">{icon}</div>
      <h2>{title}</h2>
      <p>{text}</p>
    </div>
  );
}

function App() {
  return (
    <div className="app">

      <header className="header">
        <h1>🤖 EDITH AI</h1>
        <p>AI Cybersecurity & Vision Assistant</p>
      </header>

      <div className="grid">

        <Card
          icon="📷"
          title="Vision AI"
          text="Analyze camera and images."
        />

        <Card
          icon="👤"
          title="People"
          text="Manage teachers and students."
        />

        <Card
          icon="💻"
          title="Devices"
          text="Monitor connected devices."
        />

        <Card
          icon="🛡️"
          title="Cyber Security"
          text="Logs, analysis and reports."
        />

        <Card
          icon="🤖"
          title="AI Assistant"
          text="Chat, explain and search."
        />

        <Card
          icon="⚙️"
          title="Settings"
          text="Configure EDITH AI."
        />

      </div>

    </div>
  );
}

export default App;