const express = require('express');
const cors = require('cors');
const path = require('path');
const fs = require('fs');

const app = express();

// Middleware
app.use(cors());
app.use(express.json());

// API Routes
app.get('/api/health', (req, res) => {
    res.json({ 
        status: 'success', 
        message: 'BookMyMovie Platform is running!',
        branding: 'Book Fast Feel First',
        timestamp: new Date().toISOString()
    });
});

app.get('/api/movies', (req, res) => {
    const movies = [
        {
            id: 1,
            title: "Avengers: Endgame",
            genre: "Action",
            rating: "PG-13",
            duration: "181 min",
            price: 15,
            image: "/assets/images/movie1.jpg",
            showtimes: ["10:00 AM", "2:00 PM", "6:00 PM", "10:00 PM"]
        },
        {
            id: 2,
            title: "The Lion King",
            genre: "Animation",
            rating: "PG",
            duration: "118 min",
            price: 12,
            image: "/assets/images/movie2.jpg",
            showtimes: ["11:00 AM", "3:00 PM", "7:00 PM"]
        },
        {
            id: 3,
            title: "Joker",
            genre: "Drama",
            rating: "R",
            duration: "122 min",
            price: 14,
            image: "/assets/images/movie3.jpg",
            showtimes: ["1:00 PM", "5:00 PM", "9:00 PM"]
        }
    ];
    res.json(movies);
});

app.post('/api/bookings', (req, res) => {
    const { movieId, showtime, seats, customerInfo } = req.body;
    
    // Simulate booking process
    const booking = {
        id: Math.random().toString(36).substr(2, 9),
        movieId,
        showtime,
        seats,
        customerInfo,
        status: 'confirmed',
        bookingDate: new Date().toISOString(),
        totalAmount: seats.length * 15
    };
    
    res.json({ 
        success: true, 
        booking,
        message: 'Booking confirmed! Book Fast Feel First!'
    });
});

app.get('/api/analytics', (req, res) => {
    res.json({
        totalBookings: 1247,
        totalRevenue: 18705,
        popularMovies: [
            { title: "Avengers: Endgame", bookings: 342 },
            { title: "The Lion King", bookings: 289 },
            { title: "Joker", bookings: 234 }
        ],
        branding: "Book Fast Feel First"
    });
});

// Export for Vercel
module.exports = app;