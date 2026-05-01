import "./Navbar.css";

export function Navbar() {
    return (
        <header className="nav-wrap">
            <nav className="nav-glass">
                <div className="logo">DEVO</div>
                <ul className="nav-links">
                    <li><a href="#home">Home</a></li>
                    <li><a href="#features">Features</a></li>
                    <li><a href="#contact">Contact</a></li>
                </ul>
            </nav>
        </header>
    );
}
