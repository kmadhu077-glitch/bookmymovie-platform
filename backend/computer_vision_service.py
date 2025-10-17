"""
Computer Vision Service for Cinema Management
Advanced computer vision for seat detection, occupancy monitoring, and automated theater management
"""

import cv2
import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers, Model
import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import json
import base64
from PIL import Image, ImageDraw, ImageFont
import io
import concurrent.futures
from sklearn.cluster import DBSCAN
import threading
import queue
import time

logger = logging.getLogger(__name__)

@dataclass
class SeatPosition:
    """Seat position and status information"""
    seat_id: str
    row: str
    number: int
    x_coordinate: float
    y_coordinate: float
    width: float
    height: float
    is_occupied: bool = False
    is_available: bool = True
    is_blocked: bool = False
    confidence_score: float = 0.0
    last_updated: datetime = None

@dataclass
class TheaterLayout:
    """Theater layout information"""
    theater_id: str
    screen_id: str
    total_seats: int
    rows: int
    seats_per_row: Dict[str, int]
    seat_positions: List[SeatPosition]
    camera_positions: List[Dict[str, Any]]
    calibration_data: Dict[str, Any]
    last_calibrated: datetime = None

@dataclass
class OccupancyAnalysis:
    """Theater occupancy analysis results"""
    theater_id: str
    screen_id: str
    timestamp: datetime
    total_seats: int
    occupied_seats: int
    available_seats: int
    occupancy_percentage: float
    occupancy_heatmap: List[List[float]]
    crowd_density_zones: Dict[str, float]
    predicted_peak_time: Optional[datetime] = None

@dataclass
class PersonDetection:
    """Person detection result"""
    person_id: str
    bounding_box: Tuple[int, int, int, int]  # x, y, width, height
    confidence: float
    position: Tuple[float, float]  # normalized coordinates
    is_seated: bool = False
    seat_id: Optional[str] = None
    tracking_id: Optional[str] = None

class SeatDetectionModel:
    """Deep learning model for seat detection and classification"""
    
    def __init__(self):
        self.model = None
        self.input_size = (416, 416)  # YOLO-style input size
        self.class_names = ['empty_seat', 'occupied_seat', 'blocked_seat', 'aisle', 'screen']
        self.confidence_threshold = 0.5
        self.nms_threshold = 0.4
        
    def build_model(self):
        """Build seat detection model using transfer learning"""
        
        # Base model: MobileNetV2 for efficiency
        base_model = keras.applications.MobileNetV2(
            input_shape=(*self.input_size, 3),
            include_top=False,
            weights='imagenet'
        )
        
        # Freeze base model layers
        base_model.trainable = False
        
        # Add detection head
        inputs = keras.Input(shape=(*self.input_size, 3))
        x = base_model(inputs, training=False)
        
        # Feature pyramid network layers
        x = layers.GlobalAveragePooling2D()(x)
        x = layers.Dense(512, activation='relu')(x)
        x = layers.Dropout(0.3)(x)
        
        # Classification head
        class_output = layers.Dense(len(self.class_names), activation='softmax', name='classification')(x)
        
        # Bounding box regression head
        bbox_output = layers.Dense(4, activation='linear', name='bbox_regression')(x)
        
        # Confidence score head
        confidence_output = layers.Dense(1, activation='sigmoid', name='confidence')(x)
        
        self.model = Model(inputs=inputs, outputs=[class_output, bbox_output, confidence_output])
        
        # Compile model
        self.model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=0.001),
            loss={
                'classification': 'categorical_crossentropy',
                'bbox_regression': 'mse',
                'confidence': 'binary_crossentropy'
            },
            loss_weights={
                'classification': 1.0,
                'bbox_regression': 1.0,
                'confidence': 0.5
            },
            metrics=['accuracy']
        )
        
        return self.model
    
    def preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """Preprocess image for model input"""
        
        # Resize image
        resized = cv2.resize(image, self.input_size)
        
        # Normalize pixel values
        normalized = resized.astype(np.float32) / 255.0
        
        # Add batch dimension
        return np.expand_dims(normalized, axis=0)
    
    def detect_seats(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """Detect seats in theater image"""
        
        if self.model is None:
            self.build_model()
        
        # Preprocess image
        processed_image = self.preprocess_image(image)
        
        # Run inference
        predictions = self.model.predict(processed_image, verbose=0)
        class_probs, bbox_coords, confidence_scores = predictions
        
        # Post-process results
        detections = []
        
        for i in range(len(class_probs[0])):
            confidence = confidence_scores[0][i]
            
            if confidence >= self.confidence_threshold:
                class_id = np.argmax(class_probs[0][i])
                class_name = self.class_names[class_id]
                class_confidence = class_probs[0][i][class_id]
                
                # Convert normalized bbox to pixel coordinates
                h, w = image.shape[:2]
                x, y, box_w, box_h = bbox_coords[0][i]
                x = int(x * w)
                y = int(y * h)
                box_w = int(box_w * w)
                box_h = int(box_h * h)
                
                detection = {
                    'class': class_name,
                    'confidence': float(confidence),
                    'class_confidence': float(class_confidence),
                    'bbox': [x, y, box_w, box_h],
                    'center': [x + box_w // 2, y + box_h // 2]
                }
                detections.append(detection)
        
        # Apply non-maximum suppression
        detections = self._apply_nms(detections)
        
        return detections
    
    def _apply_nms(self, detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply Non-Maximum Suppression to remove duplicate detections"""
        
        if not detections:
            return []
        
        # Convert to format expected by cv2.dnn.NMSBoxes
        boxes = []
        confidences = []
        
        for detection in detections:
            x, y, w, h = detection['bbox']
            boxes.append([x, y, w, h])
            confidences.append(detection['confidence'])
        
        # Apply NMS
        indices = cv2.dnn.NMSBoxes(
            boxes, confidences, 
            self.confidence_threshold, 
            self.nms_threshold
        )
        
        # Return filtered detections
        if len(indices) > 0:
            return [detections[i] for i in indices.flatten()]
        
        return []

class PersonTracker:
    """Multi-object tracking for people in theater"""
    
    def __init__(self):
        self.trackers = {}
        self.next_id = 1
        self.max_disappeared = 30  # frames
        self.max_distance = 100  # pixels
        
    def update(self, detections: List[PersonDetection]) -> List[PersonDetection]:
        """Update tracker with new detections"""
        
        if not detections:
            # Mark existing trackers as disappeared
            for tracker_id in list(self.trackers.keys()):
                self.trackers[tracker_id]['disappeared'] += 1
                if self.trackers[tracker_id]['disappeared'] > self.max_disappeared:
                    del self.trackers[tracker_id]
            return []
        
        # If no existing trackers, create new ones
        if not self.trackers:
            for detection in detections:
                detection.tracking_id = str(self.next_id)
                self.trackers[str(self.next_id)] = {
                    'centroid': detection.position,
                    'disappeared': 0
                }
                self.next_id += 1
            return detections
        
        # Match detections to existing trackers
        tracked_detections = []
        
        for detection in detections:
            detection.tracking_id = self._find_closest_tracker(detection.position)
            tracked_detections.append(detection)
        
        # Update tracker positions
        for detection in tracked_detections:
            if detection.tracking_id:
                self.trackers[detection.tracking_id]['centroid'] = detection.position
                self.trackers[detection.tracking_id]['disappeared'] = 0
        
        # Create new trackers for unmatched detections
        unmatched_detections = [d for d in tracked_detections if not d.tracking_id]
        for detection in unmatched_detections:
            detection.tracking_id = str(self.next_id)
            self.trackers[str(self.next_id)] = {
                'centroid': detection.position,
                'disappeared': 0
            }
            self.next_id += 1
        
        # Remove disappeared trackers
        for tracker_id in list(self.trackers.keys()):
            if tracker_id not in [d.tracking_id for d in tracked_detections]:
                self.trackers[tracker_id]['disappeared'] += 1
                if self.trackers[tracker_id]['disappeared'] > self.max_disappeared:
                    del self.trackers[tracker_id]
        
        return tracked_detections
    
    def _find_closest_tracker(self, position: Tuple[float, float]) -> Optional[str]:
        """Find the closest tracker to a detection"""
        
        min_distance = float('inf')
        closest_tracker = None
        
        for tracker_id, tracker_data in self.trackers.items():
            tracker_pos = tracker_data['centroid']
            distance = np.sqrt(
                (position[0] - tracker_pos[0]) ** 2 + 
                (position[1] - tracker_pos[1]) ** 2
            )
            
            if distance < min_distance and distance < self.max_distance:
                min_distance = distance
                closest_tracker = tracker_id
        
        return closest_tracker

class CinemaVisionService:
    """Main computer vision service for cinema management"""
    
    def __init__(self):
        self.seat_detector = SeatDetectionModel()
        self.person_tracker = PersonTracker()
        self.theaters = {}  # theater_id -> TheaterLayout
        self.active_cameras = {}  # camera_id -> camera_stream
        self.processing_threads = {}
        self.analysis_queue = queue.Queue()
        
        # Initialize person detection model (using pre-trained YOLO)
        self.person_net = None
        self._load_person_detection_model()
        
    def _load_person_detection_model(self):
        """Load pre-trained person detection model"""
        try:
            # Load YOLO model for person detection
            config_path = "models/yolo/yolov4.cfg"
            weights_path = "models/yolo/yolov4.weights"
            
            if tf.io.gfile.exists(weights_path):
                self.person_net = cv2.dnn.readNetFromDarknet(config_path, weights_path)
                logger.info("Person detection model loaded successfully")
            else:
                logger.warning("YOLO weights not found, using alternative detection")
                
        except Exception as e:
            logger.error(f"Error loading person detection model: {e}")
    
    async def calibrate_theater(self, theater_id: str, calibration_images: List[np.ndarray]) -> TheaterLayout:
        """Calibrate theater layout using reference images"""
        
        try:
            logger.info(f"Starting theater calibration for {theater_id}")
            
            # Process calibration images to detect seat layout
            all_seat_detections = []
            
            for image in calibration_images:
                seat_detections = await asyncio.get_event_loop().run_in_executor(
                    None, self.seat_detector.detect_seats, image
                )
                all_seat_detections.extend(seat_detections)
            
            # Cluster seat detections to create consistent layout
            seat_positions = self._create_seat_layout(all_seat_detections, theater_id)
            
            # Create theater layout
            theater_layout = TheaterLayout(
                theater_id=theater_id,
                screen_id=f"{theater_id}_screen_1",
                total_seats=len(seat_positions),
                rows=len(set(seat.row for seat in seat_positions)),
                seats_per_row=self._calculate_seats_per_row(seat_positions),
                seat_positions=seat_positions,
                camera_positions=[],  # Will be set separately
                calibration_data={
                    'calibration_images_count': len(calibration_images),
                    'detection_confidence_avg': np.mean([d['confidence'] for d in all_seat_detections])
                },
                last_calibrated=datetime.now()
            )
            
            # Store theater layout
            self.theaters[theater_id] = theater_layout
            
            logger.info(f"Theater {theater_id} calibrated successfully with {len(seat_positions)} seats")
            return theater_layout
            
        except Exception as e:
            logger.error(f"Theater calibration failed for {theater_id}: {e}")
            raise
    
    def _create_seat_layout(self, detections: List[Dict[str, Any]], theater_id: str) -> List[SeatPosition]:
        """Create consistent seat layout from detections"""
        
        # Filter only seat detections
        seat_detections = [
            d for d in detections 
            if d['class'] in ['empty_seat', 'occupied_seat']
        ]
        
        if not seat_detections:
            return []
        
        # Extract seat centers for clustering
        seat_centers = np.array([d['center'] for d in seat_detections])
        
        # Cluster seats by rows using DBSCAN
        clustering = DBSCAN(eps=50, min_samples=2).fit(seat_centers[:, 1:2])  # Cluster by Y coordinate
        
        seat_positions = []
        row_labels = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P']
        
        # Group seats by row clusters
        unique_clusters = set(clustering.labels_)
        unique_clusters.discard(-1)  # Remove noise points
        
        for i, cluster_id in enumerate(sorted(unique_clusters)):
            cluster_seats = [
                (seat_detections[j], seat_centers[j]) 
                for j in range(len(seat_detections))
                if clustering.labels_[j] == cluster_id
            ]
            
            # Sort seats in row by X coordinate
            cluster_seats.sort(key=lambda x: x[1][0])
            
            row_letter = row_labels[i] if i < len(row_labels) else f'R{i}'
            
            for seat_num, (detection, center) in enumerate(cluster_seats, 1):
                x, y, w, h = detection['bbox']
                
                seat_position = SeatPosition(
                    seat_id=f"{theater_id}_{row_letter}{seat_num}",
                    row=row_letter,
                    number=seat_num,
                    x_coordinate=float(center[0]),
                    y_coordinate=float(center[1]),
                    width=float(w),
                    height=float(h),
                    confidence_score=detection['confidence'],
                    last_updated=datetime.now()
                )
                seat_positions.append(seat_position)
        
        return seat_positions
    
    def _calculate_seats_per_row(self, seat_positions: List[SeatPosition]) -> Dict[str, int]:
        """Calculate number of seats per row"""
        
        seats_per_row = {}
        for seat in seat_positions:
            if seat.row not in seats_per_row:
                seats_per_row[seat.row] = 0
            seats_per_row[seat.row] += 1
        
        return seats_per_row
    
    async def analyze_occupancy(self, theater_id: str, camera_image: np.ndarray) -> OccupancyAnalysis:
        """Analyze theater occupancy from camera image"""
        
        try:
            if theater_id not in self.theaters:
                raise ValueError(f"Theater {theater_id} not calibrated")
            
            theater_layout = self.theaters[theater_id]
            
            # Detect current seats and people
            seat_detections = await asyncio.get_event_loop().run_in_executor(
                None, self.seat_detector.detect_seats, camera_image
            )
            
            person_detections = await asyncio.get_event_loop().run_in_executor(
                None, self._detect_people, camera_image
            )
            
            # Update seat occupancy based on detections
            occupied_seats = self._update_seat_occupancy(
                theater_layout, seat_detections, person_detections
            )
            
            # Calculate occupancy metrics
            total_seats = len(theater_layout.seat_positions)
            occupied_count = len(occupied_seats)
            available_count = total_seats - occupied_count
            occupancy_percentage = (occupied_count / total_seats) * 100 if total_seats > 0 else 0
            
            # Generate occupancy heatmap
            occupancy_heatmap = self._generate_occupancy_heatmap(theater_layout, occupied_seats)
            
            # Analyze crowd density zones
            crowd_density_zones = self._analyze_crowd_density(theater_layout, person_detections)
            
            analysis = OccupancyAnalysis(
                theater_id=theater_id,
                screen_id=theater_layout.screen_id,
                timestamp=datetime.now(),
                total_seats=total_seats,
                occupied_seats=occupied_count,
                available_seats=available_count,
                occupancy_percentage=occupancy_percentage,
                occupancy_heatmap=occupancy_heatmap,
                crowd_density_zones=crowd_density_zones
            )
            
            logger.info(f"Occupancy analysis completed for theater {theater_id}: {occupancy_percentage:.1f}% occupied")
            return analysis
            
        except Exception as e:
            logger.error(f"Occupancy analysis failed for theater {theater_id}: {e}")
            raise
    
    def _detect_people(self, image: np.ndarray) -> List[PersonDetection]:
        """Detect people in theater image"""
        
        people_detections = []
        
        try:
            if self.person_net is None:
                # Fallback: Use simple motion detection or background subtraction
                return self._detect_people_fallback(image)
            
            # Prepare image for YOLO
            blob = cv2.dnn.blobFromImage(
                image, 1/255.0, (416, 416), 
                swapRB=True, crop=False
            )
            
            self.person_net.setInput(blob)
            outputs = self.person_net.forward()
            
            # Process YOLO outputs
            h, w = image.shape[:2]
            
            for output in outputs:
                for detection in output:
                    scores = detection[5:]
                    class_id = np.argmax(scores)
                    confidence = scores[class_id]
                    
                    # Class 0 is 'person' in COCO dataset
                    if class_id == 0 and confidence > 0.5:
                        center_x = int(detection[0] * w)
                        center_y = int(detection[1] * h)
                        width = int(detection[2] * w)
                        height = int(detection[3] * h)
                        
                        x = int(center_x - width/2)
                        y = int(center_y - height/2)
                        
                        person_detection = PersonDetection(
                            person_id=f"person_{len(people_detections)}",
                            bounding_box=(x, y, width, height),
                            confidence=float(confidence),
                            position=(center_x/w, center_y/h)
                        )
                        people_detections.append(person_detection)
            
        except Exception as e:
            logger.error(f"Person detection error: {e}")
        
        return people_detections
    
    def _detect_people_fallback(self, image: np.ndarray) -> List[PersonDetection]:
        """Fallback person detection using traditional CV methods"""
        
        # Simple blob detection for people (placeholder implementation)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (11, 11), 0)
        
        # Find contours that might represent people
        thresh = cv2.adaptiveThreshold(
            blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY_INV, 11, 2
        )
        
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        people_detections = []
        h, w = image.shape[:2]
        
        for i, contour in enumerate(contours):
            area = cv2.contourArea(contour)
            
            # Filter by area (approximate person size)
            if 1000 < area < 10000:
                x, y, width, height = cv2.boundingRect(contour)
                center_x = x + width // 2
                center_y = y + height // 2
                
                person_detection = PersonDetection(
                    person_id=f"person_fallback_{i}",
                    bounding_box=(x, y, width, height),
                    confidence=0.6,  # Medium confidence for fallback method
                    position=(center_x/w, center_y/h)
                )
                people_detections.append(person_detection)
        
        return people_detections
    
    def _update_seat_occupancy(self, theater_layout: TheaterLayout, 
                             seat_detections: List[Dict[str, Any]], 
                             person_detections: List[PersonDetection]) -> List[str]:
        """Update seat occupancy based on detections"""
        
        occupied_seats = []
        
        # Reset all seats to unoccupied
        for seat in theater_layout.seat_positions:
            seat.is_occupied = False
        
        # Check each seat detection
        for detection in seat_detections:
            if detection['class'] == 'occupied_seat':
                # Find corresponding seat in layout
                det_center = detection['center']
                
                # Find closest seat to detection
                min_distance = float('inf')
                closest_seat = None
                
                for seat in theater_layout.seat_positions:
                    distance = np.sqrt(
                        (det_center[0] - seat.x_coordinate) ** 2 + 
                        (det_center[1] - seat.y_coordinate) ** 2
                    )
                    
                    if distance < min_distance and distance < 50:  # Within 50 pixels
                        min_distance = distance
                        closest_seat = seat
                
                if closest_seat:
                    closest_seat.is_occupied = True
                    closest_seat.confidence_score = detection['confidence']
                    closest_seat.last_updated = datetime.now()
                    occupied_seats.append(closest_seat.seat_id)
        
        # Cross-reference with person detections
        for person in person_detections:
            # Check if person is near a seat
            person_x = person.position[0] * theater_layout.seat_positions[0].x_coordinate  # Approximate scaling
            person_y = person.position[1] * theater_layout.seat_positions[0].y_coordinate
            
            for seat in theater_layout.seat_positions:
                distance = np.sqrt(
                    (person_x - seat.x_coordinate) ** 2 + 
                    (person_y - seat.y_coordinate) ** 2
                )
                
                if distance < 30:  # Person is close to seat
                    person.is_seated = True
                    person.seat_id = seat.seat_id
                    
                    if not seat.is_occupied:
                        seat.is_occupied = True
                        seat.last_updated = datetime.now()
                        occupied_seats.append(seat.seat_id)
        
        return list(set(occupied_seats))  # Remove duplicates
    
    def _generate_occupancy_heatmap(self, theater_layout: TheaterLayout, 
                                   occupied_seats: List[str]) -> List[List[float]]:
        """Generate occupancy heatmap for theater"""
        
        # Create grid based on theater dimensions
        rows = theater_layout.rows
        max_seats_per_row = max(theater_layout.seats_per_row.values()) if theater_layout.seats_per_row else 10
        
        heatmap = [[0.0 for _ in range(max_seats_per_row)] for _ in range(rows)]
        
        # Fill heatmap based on occupied seats
        for seat in theater_layout.seat_positions:
            try:
                row_index = ord(seat.row) - ord('A')  # Convert A,B,C to 0,1,2
                seat_index = seat.number - 1
                
                if 0 <= row_index < rows and 0 <= seat_index < max_seats_per_row:
                    if seat.seat_id in occupied_seats:
                        heatmap[row_index][seat_index] = 1.0  # Occupied
                    elif seat.is_available:
                        heatmap[row_index][seat_index] = 0.0  # Available
                    else:
                        heatmap[row_index][seat_index] = -1.0  # Blocked/Unavailable
            
            except (ValueError, IndexError):
                continue
        
        return heatmap
    
    def _analyze_crowd_density(self, theater_layout: TheaterLayout, 
                              person_detections: List[PersonDetection]) -> Dict[str, float]:
        """Analyze crowd density in different theater zones"""
        
        # Define theater zones
        zones = {
            'front': {'y_min': 0.0, 'y_max': 0.33},
            'middle': {'y_min': 0.33, 'y_max': 0.66},
            'back': {'y_min': 0.66, 'y_max': 1.0},
            'left': {'x_min': 0.0, 'x_max': 0.33},
            'center': {'x_min': 0.33, 'x_max': 0.66},
            'right': {'x_min': 0.66, 'x_max': 1.0}
        }
        
        zone_densities = {}
        
        for zone_name, zone_bounds in zones.items():
            people_in_zone = 0
            
            for person in person_detections:
                x, y = person.position
                
                # Check if person is in this zone
                in_zone = True
                
                if 'x_min' in zone_bounds and x < zone_bounds['x_min']:
                    in_zone = False
                if 'x_max' in zone_bounds and x > zone_bounds['x_max']:
                    in_zone = False
                if 'y_min' in zone_bounds and y < zone_bounds['y_min']:
                    in_zone = False
                if 'y_max' in zone_bounds and y > zone_bounds['y_max']:
                    in_zone = False
                
                if in_zone:
                    people_in_zone += 1
            
            # Calculate density (people per unit area)
            zone_area = 1.0  # Simplified: assume each zone has equal area
            zone_densities[zone_name] = people_in_zone / zone_area
        
        return zone_densities
    
    async def start_real_time_monitoring(self, theater_id: str, camera_stream):
        """Start real-time occupancy monitoring for theater"""
        
        if theater_id in self.processing_threads:
            logger.warning(f"Real-time monitoring already active for theater {theater_id}")
            return
        
        logger.info(f"Starting real-time monitoring for theater {theater_id}")
        
        def monitoring_loop():
            try:
                while theater_id in self.processing_threads:
                    # Read frame from camera
                    ret, frame = camera_stream.read()
                    
                    if not ret:
                        logger.error(f"Failed to read from camera for theater {theater_id}")
                        break
                    
                    # Analyze occupancy
                    try:
                        analysis = asyncio.run(self.analyze_occupancy(theater_id, frame))
                        
                        # Store analysis result
                        self.analysis_queue.put({
                            'theater_id': theater_id,
                            'analysis': analysis,
                            'timestamp': datetime.now()
                        })
                        
                    except Exception as e:
                        logger.error(f"Analysis error for theater {theater_id}: {e}")
                    
                    # Wait before next analysis
                    time.sleep(5)  # Analyze every 5 seconds
                    
            except Exception as e:
                logger.error(f"Monitoring loop error for theater {theater_id}: {e}")
            finally:
                # Cleanup
                if theater_id in self.processing_threads:
                    del self.processing_threads[theater_id]
        
        # Start monitoring thread
        thread = threading.Thread(target=monitoring_loop, daemon=True)
        self.processing_threads[theater_id] = thread
        thread.start()
    
    def stop_real_time_monitoring(self, theater_id: str):
        """Stop real-time monitoring for theater"""
        
        if theater_id in self.processing_threads:
            logger.info(f"Stopping real-time monitoring for theater {theater_id}")
            del self.processing_threads[theater_id]
    
    def get_latest_analysis(self, theater_id: str) -> Optional[OccupancyAnalysis]:
        """Get latest occupancy analysis for theater"""
        
        latest_analysis = None
        
        # Search through analysis queue for latest result
        temp_queue = queue.Queue()
        
        while not self.analysis_queue.empty():
            try:
                analysis_data = self.analysis_queue.get_nowait()
                
                if analysis_data['theater_id'] == theater_id:
                    if (latest_analysis is None or 
                        analysis_data['timestamp'] > latest_analysis['timestamp']):
                        latest_analysis = analysis_data
                
                temp_queue.put(analysis_data)
                
            except queue.Empty:
                break
        
        # Put items back in queue
        while not temp_queue.empty():
            self.analysis_queue.put(temp_queue.get())
        
        return latest_analysis['analysis'] if latest_analysis else None
    
    async def generate_theater_report(self, theater_id: str, 
                                    start_time: datetime, 
                                    end_time: datetime) -> Dict[str, Any]:
        """Generate comprehensive theater analysis report"""
        
        try:
            if theater_id not in self.theaters:
                raise ValueError(f"Theater {theater_id} not found")
            
            theater_layout = self.theaters[theater_id]
            
            # Collect analysis data (this would come from stored historical data)
            report = {
                'theater_id': theater_id,
                'report_period': {
                    'start': start_time.isoformat(),
                    'end': end_time.isoformat()
                },
                'theater_info': {
                    'total_seats': theater_layout.total_seats,
                    'rows': theater_layout.rows,
                    'seats_per_row': theater_layout.seats_per_row
                },
                'occupancy_statistics': {
                    'average_occupancy': 65.2,  # Placeholder - would calculate from historical data
                    'peak_occupancy': 95.8,
                    'lowest_occupancy': 12.3,
                    'peak_times': ['19:00-21:00', '14:00-16:00'],
                    'low_times': ['10:00-12:00', '22:00-24:00']
                },
                'crowd_patterns': {
                    'popular_sections': ['middle_center', 'back_center'],
                    'underutilized_sections': ['front_left', 'front_right'],
                    'movement_patterns': 'Most people prefer center seats, avoid front rows'
                },
                'recommendations': [
                    'Consider dynamic pricing for front row seats',
                    'Peak capacity reached during evening shows',
                    'Optimize cleaning schedule around low-occupancy periods'
                ]
            }
            
            return report
            
        except Exception as e:
            logger.error(f"Report generation failed for theater {theater_id}: {e}")
            raise

# Global computer vision service
computer_vision_service = CinemaVisionService()

# Utility functions
async def calibrate_cinema_theater(theater_id: str, calibration_images: List[str]) -> TheaterLayout:
    """Calibrate theater using base64 encoded images"""
    
    # Convert base64 images to numpy arrays
    images = []
    for img_b64 in calibration_images:
        img_data = base64.b64decode(img_b64)
        img_array = np.array(Image.open(io.BytesIO(img_data)))
        images.append(img_array)
    
    return await computer_vision_service.calibrate_theater(theater_id, images)

async def get_theater_occupancy(theater_id: str, camera_image_b64: str) -> OccupancyAnalysis:
    """Get current theater occupancy from camera image"""
    
    # Convert base64 image to numpy array
    img_data = base64.b64decode(camera_image_b64)
    img_array = np.array(Image.open(io.BytesIO(img_data)))
    
    return await computer_vision_service.analyze_occupancy(theater_id, img_array)

async def start_theater_monitoring(theater_id: str, camera_url: str):
    """Start real-time theater monitoring"""
    
    # Open camera stream
    camera = cv2.VideoCapture(camera_url)
    
    await computer_vision_service.start_real_time_monitoring(theater_id, camera)

def stop_theater_monitoring(theater_id: str):
    """Stop real-time theater monitoring"""
    computer_vision_service.stop_real_time_monitoring(theater_id)

def get_current_occupancy(theater_id: str) -> Optional[OccupancyAnalysis]:
    """Get latest occupancy data for theater"""
    return computer_vision_service.get_latest_analysis(theater_id)