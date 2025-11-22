import React from 'react';
import Map from '../components/map/Map';

const Home: React.FC = () => {
    return (
        <div className="home-page">
            <div className="map-section">
                <Map />
            </div>
        </div>
    );
};

export default Home;
