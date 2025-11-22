import React from 'react';
import { Routes, Route } from 'react-router-dom';
import MainLayout from './layout/MainLayout';
import Home from './pages/Home';
import StackPage from './pages/StackPage';
import "./global.scss"

function App() {
    return (
        <MainLayout>
            <Routes>
                <Route path="/" element={<Home />} />
                <Route path="/stack/:id" element={<StackPage />} />
            </Routes>
        </MainLayout>
    );
}

export default App;
