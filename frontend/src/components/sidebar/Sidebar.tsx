import Calendar from "../calendar/Calendar";
import React from 'react';
import { useNavigate } from 'react-router-dom';
import { stacks } from '../../data/stacks';
import './Sidebar.scss';

const Sidebar: React.FC = () => {
    const navigate = useNavigate();

    return (
        <div className="sidebar">
            <div className="stacks">
                {stacks.map(stack => (
                    <div
                        key={stack.id}
                        className="stack-item"
                        onClick={() => navigate(`/stack/${stack.id}`)}
                    >
                        <span>{stack.name}</span>
                        <span
                            className={`status-dot ${stack.status.replace(/\s+/g, '-').toLowerCase()}`}
                            title={stack.status}
                        ></span>
                    </div>
                ))}
            </div>

            <div className="calendar-section">
                <Calendar
                    events={[
                        { date: "2025-11-22", status: "green", stackId: 1 },
                        { date: "2025-11-25", status: "yellow", stackId: 2 },
                        { date: "2025-12-15", status: "red", stackId: 3 },
                        { date: "2025-12-8", status: "green", stackId: 1 },
                    ]}
                />
            </div>
        </div>
    );
};

export default Sidebar;
