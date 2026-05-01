import "./App.css";
import { Navbar } from "./components/Navbar";

function App() {
    return (
        <div className="page">
            <Navbar />
            <main>
                <section className="hero section">
                    <h1>Devo Frontend</h1>
                    <p>Build interfaces with clear hierarchy and polish.</p>
                    <button className="cta">Start Building</button>
                </section>
                <section className="features section">
                    <h2>Features</h2>
                    <div className="cards">
                        <article className="card">Fast iteration</article>
                        <article className="card">Safe tools</article>
                        <article className="card">Session memory</article>
                    </div>
                </section>
                <section className="contact section">
                    <h2>Contact</h2>
                    <p>Ready to ship your next idea with Devo.</p>
                </section>
            </main>
        </div>
    );
}

export default App;
