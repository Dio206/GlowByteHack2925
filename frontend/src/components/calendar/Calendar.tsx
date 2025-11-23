import React, { useState } from "react";
import "./Calendar.scss";

type EventStatus = "green" | "red" | "yellow";

interface CalendarEvent {
    date: string; // "2025-01-15"
    status: EventStatus;
    stackId: number;
}

interface CalendarProps {
    events?: CalendarEvent[];
}

const Calendar: React.FC<CalendarProps> = ({ events = [] }) => {
    const [date, setDate] = useState(new Date());

    const currentYear = date.getFullYear();
    const currentMonth = date.getMonth();

    const today = new Date();
    const isCurrentMonth =
        today.getFullYear() === currentYear &&
        today.getMonth() === currentMonth;

    const daysInMonth = new Date(currentYear, currentMonth + 1, 0).getDate();
    const firstDayIndex = new Date(currentYear, currentMonth, 1).getDay();
    const normalizedFirstDay = (firstDayIndex + 6) % 7;

    const prevMonth = () => setDate(new Date(currentYear, currentMonth - 1, 1));
    const nextMonth = () => setDate(new Date(currentYear, currentMonth + 1, 1));

    const monthEvents = events.filter((event) => {
        const eventDate = new Date(event.date);
        return (
            eventDate.getFullYear() === currentYear &&
            eventDate.getMonth() === currentMonth
        );
    });

    const getEventForDay = (day: number) => {
        return monthEvents.find(
            (e) => new Date(e.date).getDate() === day
        );
    };

    const monthNames = [
        "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
        "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
    ];

    const weekDays = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"];

    return (
        <div className="calendar">
            <div className="calendar-header">
                <button onClick={prevMonth} className="nav-btn">&lt;</button>

                <p className="calendar-title">
                    {monthNames[currentMonth]} {currentYear}
                </p>

                <button onClick={nextMonth} className="nav-btn">&gt;</button>
            </div>

            <div className="calendar-weekdays">
                {weekDays.map((d, i) => (
                    <div
                        key={d}
                        className={`weekday ${i === 5 || i === 6 ? "weekend-title" : ""}`}
                    >
                        {d}
                    </div>
                ))}
            </div>

            <div className="calendar-days">

                {Array.from({ length: normalizedFirstDay }).map((_, i) => (
                    <div key={`empty-${i}`} className="empty"></div>
                ))}

                {Array.from({ length: daysInMonth }).map((_, i) => {
                    const day = i + 1;
                    const event = getEventForDay(day);
                    const isToday = isCurrentMonth && today.getDate() === day;

                    return (
                        <div
                            key={day}
                            className={`day 
                ${isToday ? "today" : ""} 
                ${event ? `event-${event.status}` : ""}
              `}
                            data-stack={event?.stackId}
                        >
                            {day}
                        </div>
                    );
                })}
            </div>
        </div>
    );
};

export default Calendar;
