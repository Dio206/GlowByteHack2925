import React from 'react';
import Sidebar from "../components/sidebar/Sidebar";
import './MainLayout.scss';

interface Props {
    children: React.ReactNode;
}

const MainLayout: React.FC<Props> = ({ children }) => {
    return (
        <div className="layout">
            <Sidebar />
            <div className="content">{children}</div>
        </div>
    );
};

export default MainLayout;
