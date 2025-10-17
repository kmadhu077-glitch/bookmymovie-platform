"""
Sample Data Generator for BookMyMovie Analytics Demo
Creates realistic sample data to showcase analytics capabilities
"""

import random
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from models import (
    get_db, User, Movie, Theater, Screen, Showtime, 
    Booking, Payment, Review, Analytics
)
from db_config import get_database_session

def generate_sample_data():
    """Generate comprehensive sample data for analytics demo"""
    print("Generating sample data for analytics demo...")
    
    db = next(get_database_session())
    
    try:
        # Check if data already exists
        existing_users = db.query(User).count()
        if existing_users > 0:
            print(f"Found {existing_users} existing users. Skipping data generation.")
            return
        
        # Generate Users (100 users)
        print("Creating users...")
        users = []
        for i in range(100):
            days_ago = random.randint(1, 90)
            created_date = datetime.now() - timedelta(days=days_ago)
            
            user = User(
                username=f"user{i+1:03d}",
                email=f"user{i+1:03d}@bookmymovie.com",
                password_hash="hashed_password_123",
                full_name=f"User {i+1}",
                phone=f"+1-555-{random.randint(1000,9999)}",
                created_at=created_date
            )
            users.append(user)
            db.add(user)
        
        db.commit()
        print(f"Created {len(users)} users")
        
        # Generate Movies (20 popular movies)
        print("Creating movies...")
        movie_titles = [
            "Avatar: The Way of Water", "Top Gun: Maverick", "Black Panther: Wakanda Forever",
            "Jurassic World Dominion", "Doctor Strange in the Multiverse of Madness",
            "Minions: The Rise of Gru", "Thor: Love and Thunder", "The Batman",
            "Morbius", "Sonic the Hedgehog 2", "Fantastic Beasts: The Secrets of Dumbledore",
            "The Northman", "Everything Everywhere All at Once", "Nope",
            "Bullet Train", "Elvis", "Lightyear", "The Bad Guys", "Spider-Man: No Way Home",
            "Dune", "No Time to Die", "Fast & Furious 9"
        ]
        
        movies = []
        for i, title in enumerate(movie_titles):
            movie = Movie(
                title=title,
                description=f"An amazing movie about {title.lower()}",
                duration=random.randint(90, 180),
                genre=random.choice(["Action", "Comedy", "Drama", "Sci-Fi", "Adventure"]),
                rating=round(random.uniform(6.5, 9.5), 1),
                release_date=datetime.now() - timedelta(days=random.randint(30, 365)),
                poster_url=f"https://example.com/posters/{title.lower().replace(' ', '-')}.jpg"
            )
            movies.append(movie)
            db.add(movie)
        
        db.commit()
        print(f"Created {len(movies)} movies")
        
        # Generate Theaters (5 theaters)
        print("Creating theaters...")
        theater_names = [
            "CineMax Downtown", "StarPlex Mall", "MovieWorld Central", 
            "Grand Cinema", "Metro Multiplex"
        ]
        
        theaters = []
        for name in theater_names:
            theater = Theater(
                name=name,
                location=f"{name} Location, Movie City",
                address=f"123 {name} Street, Movie City, MC 12345",
                phone=f"+1-555-{random.randint(1000,9999)}",
                email=f"info@{name.lower().replace(' ', '')}.com"
            )
            theaters.append(theater)
            db.add(theater)
        
        db.commit()
        print(f"Created {len(theaters)} theaters")
        
        # Generate Screens (4-6 screens per theater)
        print("Creating screens...")
        screens = []
        for theater in theaters:
            num_screens = random.randint(4, 6)
            for screen_num in range(1, num_screens + 1):
                screen = Screen(
                    theater_id=theater.id,
                    screen_number=screen_num,
                    capacity=random.choice([100, 120, 150, 180, 200]),
                    screen_type=random.choice(["Standard", "IMAX", "Dolby Atmos", "4DX"])
                )
                screens.append(screen)
                db.add(screen)
        
        db.commit()
        print(f"Created {len(screens)} screens")
        
        # Generate Showtimes (multiple showtimes per movie/screen combination)
        print("Creating showtimes...")
        showtimes = []
        for movie in movies:
            # Each movie shows in 2-4 different screens
            selected_screens = random.sample(screens, random.randint(2, 4))
            
            for screen in selected_screens:
                # 2-4 showtimes per day for the past 30 days
                for day in range(30):
                    show_date = datetime.now() - timedelta(days=day)
                    
                    # 2-4 shows per day
                    for show_time in ["14:00", "17:30", "20:00", "22:30"][:random.randint(2, 4)]:
                        hour, minute = map(int, show_time.split(":"))
                        showtime_dt = show_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
                        
                        showtime = Showtime(
                            movie_id=movie.id,
                            screen_id=screen.id,
                            showtime=showtime_dt,
                            price=round(random.uniform(8.0, 18.0), 2)
                        )
                        showtimes.append(showtime)
                        db.add(showtime)
        
        db.commit()
        print(f"Created {len(showtimes)} showtimes")
        
        # Generate Bookings (realistic booking patterns)
        print("Creating bookings...")
        bookings = []
        payments = []
        
        for showtime in random.sample(showtimes, len(showtimes) // 3):  # 1/3 of showtimes have bookings
            # 1-3 bookings per showtime
            for _ in range(random.randint(1, 3)):
                user = random.choice(users)
                num_seats = random.randint(1, 4)
                
                # Generate realistic seat selection
                seats = []
                for i in range(num_seats):
                    row = random.choice(["A", "B", "C", "D", "E", "F", "G", "H"])
                    seat_num = random.randint(1, 15)
                    seats.append(f"{row}{seat_num}")
                
                booking_date = showtime.showtime - timedelta(days=random.randint(0, 14))
                
                booking = Booking(
                    user_id=user.id,
                    showtime_id=showtime.id,
                    seats=",".join(seats),
                    total_amount=showtime.price * num_seats,
                    status=random.choice(["confirmed", "completed", "confirmed", "completed"]),  # Mostly successful
                    booking_date=booking_date
                )
                bookings.append(booking)
                db.add(booking)
                db.flush()  # Get booking ID
                
                # Create payment for booking
                payment = Payment(
                    booking_id=booking.id,
                    amount=booking.total_amount,
                    payment_method=random.choice(["credit_card", "debit_card", "paypal", "apple_pay"]),
                    status="completed",
                    transaction_id=f"txn_{random.randint(100000, 999999)}",
                    payment_date=booking_date + timedelta(minutes=random.randint(1, 30))
                )
                payments.append(payment)
                db.add(payment)
        
        db.commit()
        print(f"Created {len(bookings)} bookings and {len(payments)} payments")
        
        # Generate Reviews (60% of completed bookings get reviews)
        print("Creating reviews...")
        reviews = []
        completed_bookings = [b for b in bookings if b.status == "completed"]
        
        for booking in random.sample(completed_bookings, int(len(completed_bookings) * 0.6)):
            movie_id = db.query(Showtime.movie_id).filter(Showtime.id == booking.showtime_id).scalar()
            
            review = Review(
                user_id=booking.user_id,
                movie_id=movie_id,
                rating=random.randint(3, 5),  # Mostly positive reviews
                comment=random.choice([
                    "Great movie! Loved every minute of it.",
                    "Excellent cinematography and acting.",
                    "A bit long but worth watching.",
                    "Amazing special effects!",
                    "Would definitely recommend to friends.",
                    "Good story and great performances.",
                    "Entertaining and well-made film."
                ]),
                review_date=booking.booking_date + timedelta(days=random.randint(1, 7))
            )
            reviews.append(review)
            db.add(review)
        
        db.commit()
        print(f"Created {len(reviews)} reviews")
        
        # Generate Analytics entries (daily summaries)
        print("Creating analytics entries...")
        analytics = []
        
        for day in range(30):
            date = datetime.now() - timedelta(days=day)
            date_str = date.strftime('%Y-%m-%d')
            
            # Calculate daily stats
            day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            
            daily_bookings = [b for b in bookings if day_start <= b.booking_date < day_end]
            daily_revenue = sum([p.amount for p in payments if day_start <= p.payment_date < day_end])
            daily_users = len(set([b.user_id for b in daily_bookings]))
            
            analytics_entry = Analytics(
                date=date_str,
                metric_name="daily_summary",
                metric_value=len(daily_bookings),
                additional_data=f"revenue:{daily_revenue:.2f},users:{daily_users}"
            )
            analytics.append(analytics_entry)
            db.add(analytics_entry)
        
        db.commit()
        print(f"Created {len(analytics)} analytics entries")
        
        # Print summary
        print("\n" + "="*60)
        print("SAMPLE DATA GENERATION COMPLETE!")
        print("="*60)
        print(f"Users: {len(users)}")
        print(f"Movies: {len(movies)}")
        print(f"Theaters: {len(theaters)}")
        print(f"Screens: {len(screens)}")
        print(f"Showtimes: {len(showtimes)}")
        print(f"Bookings: {len(bookings)}")
        print(f"Payments: {len(payments)}")
        print(f"Reviews: {len(reviews)}")
        print(f"Analytics: {len(analytics)}")
        
        total_revenue = sum([p.amount for p in payments])
        print(f"\nTotal Revenue: ${total_revenue:,.2f}")
        print(f"Average Ticket Price: ${total_revenue/len(payments):.2f}")
        print(f"Booking Success Rate: {(len([b for b in bookings if b.status in ['confirmed', 'completed']]) / len(bookings) * 100):.1f}%")
        
        print("\n🎉 Analytics Dashboard is now ready with realistic sample data!")
        print("🔗 Visit: http://localhost:8080/analytics-dashboard.html")
        
    except Exception as e:
        db.rollback()
        print(f"Error generating sample data: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    generate_sample_data()