import React, { useEffect, useState } from "react";
import "./Calendar.scss";

type EventStatus = "risk";

interface CalendarEvent {
    date: string;
    stackId: number;
    status: EventStatus;
}

const Calendar: React.FC = () => {
    const [date, setDate] = useState(new Date());
    const [events, setEvents] = useState<CalendarEvent[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

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

    useEffect(() => {
        const fetchEvents = async () => {
            setLoading(true);
            try {
                const res = await fetch("http://localhost:8000/risk_calendar_dates");
                if (!res.ok) throw new Error(`Ошибка ${res.status}`);
                const data: Record<string, string[]> = await res.json();

                // Преобразуем JSON в массив событий для календаря
                const eventsArray: CalendarEvent[] = [];
                Object.entries(data).forEach(([stackId, dates]) => {
                    dates.forEach((d) => {
                        eventsArray.push({
                            date: d,
                            stackId: parseInt(stackId),
                            status: "risk"
                        });
                    });
                });

                setEvents(eventsArray);
                setError(null);
            } catch (err: any) {
                console.error("Ошибка загрузки календаря:", err);
                setEvents([]);
            } finally {
                setLoading(false);
            }
        };

        fetchEvents();
    }, []);

    const monthEvents = events.filter((event) => {
        const eventDate = new Date(event.date);
        return (
            eventDate.getFullYear() === currentYear &&
            eventDate.getMonth() === currentMonth
        );
    });

    const getEventsForDay = (day: number) => {
        return monthEvents.filter(
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
                <p className="calendar-title">{monthNames[currentMonth]} {currentYear}</p>
                <button onClick={nextMonth} className="nav-btn">&gt;</button>
            </div>

            {loading && <div className="calendar-loading">Загрузка...</div>}
            {error && <div className="calendar-error">{error}</div>}

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
                    const dayEvents = getEventsForDay(day);
                    const isToday = isCurrentMonth && today.getDate() === day;

                    return (
                        <div
                            key={day}
                            className={`day ${isToday ? "today" : ""} ${dayEvents.length ? "event-risk" : ""}`}
                            data-stack={dayEvents.map(e => e.stackId).join(",")}
                            title={dayEvents.length ? `Риск: штабели ${dayEvents.map(e => e.stackId).join(", ")}` : ""}
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
