const express = require('express');
const cors = require('cors');
const path = require('path');
const fs = require('fs');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.static('frontend'));

// Serve static files
app.use('/assets', express.static('frontend/assets'));
app.use('/css', express.static('frontend/css'));
app.use('/js', express.static('frontend/js'));

// Main routes
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'frontend', 'index.html'));
});

app.get('/admin', (req, res) => {
    res.sendFile(path.join(__dirname, 'frontend', 'admin.html'));
});

app.get('/booking', (req, res) => {
    res.sendFile(path.join(__dirname, 'frontend', 'booking.html'));
});

app.get('/movies', (req, res) => {
    res.sendFile(path.join(__dirname, 'frontend', 'movies.html'));
});

app.get('/analytics', (req, res) => {
    res.sendFile(path.join(__dirname, 'frontend', 'analytics.html'));
});

// API endpoints
app.get('/api/health', (req, res) => {
    res.json({ 
        status: 'healthy', 
        message: 'BookMyMovie Platform - Book Fast Feel First!',
        timestamp: new Date().toISOString()
    });
});

app.get('/api/movies', (req, res) => {
    const movies = [
        {
            id: 1,
            title: "Avatar: The Way of Water",
            genre: "Sci-Fi",
            duration: "192 min",
            rating: "PG-13",
            price: 15.99,
            showTimes: ["10:00 AM", "2:00 PM", "6:00 PM", "10:00 PM"]
        },
        {
            id: 2,
            title: "Top Gun: Maverick",
            genre: "Action",
            duration: "130 min",
            rating: "PG-13",
            price: 14.99,
            showTimes: ["11:00 AM", "3:00 PM", "7:00 PM", "11:00 PM"]
        },
        {
            id: 3,
            title: "The Batman",
            genre: "Action",
            duration: "176 min",
            rating: "PG-13",
            price: 16.99,
            showTimes: ["12:00 PM", "4:00 PM", "8:00 PM"]
        }
    ];
    res.json(movies);
});

app.post('/api/bookings', (req, res) => {
    const booking = {
        id: Date.now(),
        movieId: req.body.movieId,
        seats: req.body.seats,
        showTime: req.body.showTime,
        totalPrice: req.body.totalPrice,
        customerInfo: req.body.customerInfo,
        bookingTime: new Date().toISOString(),
        status: 'confirmed'
    };
    
    res.json({
        success: true,
        message: 'Booking confirmed - Book Fast Feel First!',
        booking: booking
    });
});

// Start server
app.listen(PORT, () => {
    console.log(`🎬 BookMyMovie Platform running on port ${PORT}`);
    console.log(`🚀 Book Fast Feel First!`);
    console.log(`📱 Access your platform at: http://localhost:${PORT}`);
});

module.exports = app;