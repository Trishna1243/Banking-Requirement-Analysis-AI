import React from "react";
import { NavLink } from "react-router-dom";

function Layout({ children }) {
  return (
    <div className="app">

      <aside>

        <div className="brand">

          <b>R</b>

          <div>
            <strong>ReqAI</strong>
            <small>Requirement Intelligence</small>
          </div>

        </div>

        <nav>

          <NavLink to="/" end>
            ⌂ Dashboard
          </NavLink>

          <NavLink to="/analyze">
            ↑ Analyze
          </NavLink>

          <NavLink to="/results">
            ▣ Results
          </NavLink>

        </nav>

        <div className="status">

          ● AI Engine

          <br />

          <small>
            Ready for analysis
          </small>

        </div>

      </aside>

      <main>
        {children}
      </main>

    </div>
  );
}

export default Layout;