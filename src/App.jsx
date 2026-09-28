import { Analytics } from '@vercel/analytics/react';
import './App.css';

function App() {
  return (
    <>
      <div className="container">
        <header>
          <h1>Luis Santos</h1>
          <p>GitHub Profile</p>
        </header>
        
        <main>
          <section className="profile">
            <h2>Welcome to my profile</h2>
            <p>This is a Vite + React application with Vercel Web Analytics integrated.</p>
            
            <div className="links">
              <a href="https://github.com/luisssantos56" target="_blank" rel="noopener noreferrer">
                GitHub Profile
              </a>
              <a href="https://www.instagram.com/luis_.ssantos" target="_blank" rel="noopener noreferrer">
                Instagram
              </a>
            </div>
          </section>
          
          <section className="visualizations">
            <h3>GitHub Contribution Visualizations</h3>
            <div className="svg-container">
              <img src="/luis-heatmap.svg" alt="Contribution Heatmap" />
            </div>
          </section>
        </main>
      </div>
      
      {/* Vercel Web Analytics - tracks page views and web vitals */}
      <Analytics />
    </>
  );
}

export default App;
