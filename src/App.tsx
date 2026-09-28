import { Analytics } from '@vercel/analytics/react';
import './App.css'

function App() {
  return (
    <>
      <div className="container">
        <div className="header">
          <h3><code>luis@github ~ $ whoami</code></h3>
        </div>

        <div className="content">
          <div className="images">
            <img src="/luis-ascii.svg" alt="Luis Santos — ASCII portrait" className="ascii-portrait" />
            <img src="/luis-wordmark.svg" alt="LUIS — 3D ASCII wordmark" className="wordmark" />
          </div>

          <div className="contributions">
            <h3><code>luis@github ~ $ ./contributions.sh</code></h3>
            <img src="/luis-heatmap.svg" alt="Luis's GitHub contribution graph" className="heatmap" />
          </div>

          <div className="links">
            <h3><code>luis@github ~ $ ./links.sh</code></h3>
            <a href="https://www.instagram.com/luis_.ssantos" target="_blank" rel="noopener noreferrer">
              <img src="https://img.shields.io/badge/Instagram-luis__.ssantos-E4405F?style=for-the-badge&logo=instagram&logoColor=white" alt="Instagram" />
            </a>
          </div>
        </div>
      </div>
      
      {/* Vercel Web Analytics component as per documentation */}
      <Analytics />
    </>
  )
}

export default App
