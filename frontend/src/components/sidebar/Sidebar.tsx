import Calendar from "../calendar/Calendar";
import React from 'react';
import { useNavigate } from 'react-router-dom';
import './Sidebar.scss';

const demoStacks = Array.from({ length: 30 }, (_, i) => ({
    id: i + 1,
    name: `Штабель ${i + 1}`,
}));

const Sidebar: React.FC = () => {
    const navigate = useNavigate();

    return (
        <div className="sidebar">
            <div className="stacks">
                {demoStacks.map(stack => (
                    <div
                        key={stack.id}
                        className="stack-item"
                        onClick={() => navigate(`/stack/${stack.id}`)}
                    >
                        {stack.name}
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
