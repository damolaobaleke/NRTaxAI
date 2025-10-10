import React from 'react'
import { BrowserRouter as Router } from 'react-router-dom';
import {Route, Routes} from 'react-router'
import './App.css';
import LandingPage from './LandingPage';

function App() {
	return (
		<Router>
            <div className="App">
                <Routes>
                    <Route path="/"  element={<LandingPage/>}/>
                </Routes>
            </div>
        </Router>
  );
}
export default App;
