import React from 'react'
import { createRoot } from 'react-dom/client'
import HomePage from './pages/HomePage.jsx'
import SignInPage from './pages/SignInPage.jsx'
import WelcomePage from './pages/WelcomePage.jsx'
import ControlRoomDashboard from './pages/ControlRoomDashboard.jsx'
import AdminDashboard from './pages/AdminDashboard.jsx'
import './styles.css'

const path = window.location.pathname
const Page = path === '/sign-in' ? SignInPage : path === '/welcome' ? WelcomePage : path === '/control-room' ? ControlRoomDashboard : path === '/admin' ? AdminDashboard : HomePage

createRoot(document.getElementById('root')).render(<Page />)
