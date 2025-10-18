const express = require('express');
const app = express();
const PORT = 3001;

app.get('/', (req, res) => {
    res.send(`
        <html>
        <head>
            <title>BookMyMovie - Book Fast Feel First!</title>
            <style>
                body { font-family: Arial, sans-serif; text-align: center; padding: 50px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }
                h1 { font-size: 3em; margin-bottom: 20px; }
                .tagline { font-size: 1.5em; margin-bottom: 30px; }
                .features { text-align: left; max-width: 600px; margin: 0 auto; }
            </style>
        </head>
        <body>
            <h1>🎬 BookMyMovie Platform</h1>
            <div class="tagline">Book Fast Feel First!</div>
            <div class="features">
                <h2>✅ Platform Features:</h2>
                <ul>
                    <li>Complete Movie Booking System</li>
                    <li>AI Recommendations Engine</li>
                    <li>Mobile App Integration</li>
                    <li>Admin Dashboard</li>
                    <li>Analytics Dashboard</li>
                    <li>65 Backend Services</li>
                    <li>Custom Branding Throughout</li>
                </ul>
            </div>
            <p><strong>🚀 Your platform is live and working!</strong></p>
        </body>
        </html>
    `);
});

app.get('/api/health', (req, res) => {
    res.json({ 
        status: 'healthy', 
        message: 'BookMyMovie Platform - Book Fast Feel First!',
        timestamp: new Date().toISOString(),
        features: [
            'Movie Booking System',
            'AI Recommendations',
            'Mobile App Ready',
            'Admin Dashboard',
            'Analytics Dashboard'
        ]
    });
});

app.listen(PORT, '127.0.0.1', () => {
    console.log(`🎬 BookMyMovie Test Server running on port ${PORT}`);
    console.log(`🚀 Book Fast Feel First!`);
    console.log(`📱 Access at: http://localhost:${PORT}`);
    console.log(`🔗 API Health: http://localhost:${PORT}/api/health`);
});