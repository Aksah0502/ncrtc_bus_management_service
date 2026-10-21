# NCRTC Bus Management System

## Project Overview

The NCRTC Bus Management System (BMS) is a student capstone project designed to support feeder-bus operations around the Delhi-NCR rapid-rail corridor. It brings bus location tracking, route and duty scheduling, incident management, and driver notices together in one application.

The project follows a scoped demonstration approach using seeded dummy data and simulated GPS updates. It is not intended to connect to real GPS hardware or operate as a production transport platform.

## Objectives

- View current bus locations and review recorded trip paths.
- Plan routes and assign drivers and vehicles to daily duties.
- Report, assign, track, and resolve operational incidents.
- Publish notices for drivers and track notice readership.
- Provide role-based access to operational information and reports.

## User Roles

- **Driver:** Views today's published duty, acknowledges the assignment, reads relevant notices, and reports incidents. The driver app includes a panic action that creates a critical incident.
- **Depot Manager:** Manages the depot's weekly duty roster, assigns drivers to vehicles and routes, views depot buses on a map, and handles depot incidents.
- **Control-Room Operator:** Monitors buses across depots, reviews vehicle location history, responds to alerts, and assigns serious incidents.
- **Administrator:** Manages users, vehicles, depots, and routes; publishes notices; and reviews notice read receipts.
- **Executive (read-only):** Views the previous day's operational report and may download it as a PDF.

## Core Modules and Functionality

### 1. AVLS — Automatic Vehicle Location System
- Display active vehicles on a map with vehicle registration and current speed.
- Refresh displayed locations every 5–10 seconds using simulated GPS updates.
- Filter the map by depot.
- View a selected vehicle's assigned driver, route, and recent location trail.
- Retrieve the recorded path for a selected vehicle and date.

### 2. Scheduling — Routes and Duties
- Manage routes, ordered stops, and planned arrival timings.
- View a weekly roster organised by drivers and dates.
- Assign a driver, vehicle, and route to a duty.
- Publish the roster so drivers can view their assigned duties.
- Record a driver's acknowledgement with a timestamp.

### 3. IMS — Incident Management System
- Raise incidents such as breakdowns, accidents, complaints, or other operational issues.
- Record severity, description, and an optional vehicle association or photograph.
- Create a P1 incident from the driver's panic action, associating available vehicle and location information.
- Filter incidents by status, severity, depot, and incidents raised by the current user.
- Track status changes, notes, assignments, and incident history.
- Support the status flow: Open → Acknowledged → In Progress → Resolved → Closed.

### 4. CMS — Content Management System
- Create notices with a title, message, publication date, and target audience.
- Target notices to all drivers, a specific depot, or a specific role.
- Show unread notices to drivers and record when a notice is read.
- Let administrators review which drivers have and have not read a notice.

### 5. Authentication and Access Control
- Provide login for authorised users.
- Support role-based access for the project's user roles.
- Restrict drivers and depot managers to the appropriate depot-related information; control-room operators and administrators have system-wide access as defined by the project brief.

### 6. Operational Reporting
- Provide the executive with the previous day's operational report.
- Support PDF download as a planned reporting capability.

## Technology Stack

The following is the recommended stack for the project:

- **Backend:** Python with FastAPI
- **Database:** PostgreSQL with PostGIS for geographic data
- **ORM and migrations:** SQLAlchemy and Alembic
- **Frontend:** React with Vite
- **Maps:** Leaflet with OpenStreetMap tiles
- **Driver experience:** Mobile-friendly Progressive Web App (PWA)
- **Authentication:** JWT-based sessions and bcrypt password hashing
- **Containers:** Docker and Docker Compose
- **Testing and CI:** Pytest / Vitest and GitHub Actions

## Project Scope

- Uses seeded demonstration data for depots, vehicles, users, routes, duties, incidents, notices, and GPS history.
- Simulates bus movement through a small background process or replayed GPS data.
- Focuses on the core four modules: AVLS, Scheduling, IMS, and CMS, with authentication and role-based access as shared capabilities.
- Is scoped for a student project, rather than a production-grade GPS ingestion platform.

## Scope Note

The project brief's user-role overview lists **Executive (read-only)** as the fifth role, while its authentication section lists **Conductor** instead. The final role set should be confirmed before role-specific functionality and permissions are finalized.
