import React from 'react';
import { useNavigate } from 'react-router-dom';
import { stacks } from '../../data/stacks';
import './Map.scss';

const Map: React.FC = () => {
    const navigate = useNavigate();

    return (
        <div className="map-container">
            <img src="/russia.svg" alt="Карта России" className="map-image" />

            {stacks.map(stack => (
                <div
                    key={stack.id}
                    className="map-point"
                    style={{
                        left: `${stack.x}%`,
                        top: `${stack.y}%`
                    }}
                    onClick={() => navigate(`/stack/${stack.id}`)}
                    title={stack.name}
                />
            ))}
        </div>
    );
};

export default Map;
