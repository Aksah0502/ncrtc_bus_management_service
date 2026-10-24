import React from 'react'
import { createRoot } from 'react-dom/client'
import HomePage from './pages/HomePage.jsx'
import SignInPage from './pages/SignInPage.jsx'
import WelcomePage from './pages/WelcomePage.jsx'
import './styles.css'

const path = window.location.pathname
const Page = path === '/sign-in' ? SignInPage : path === '/welcome' ? WelcomePage : HomePage

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <Page />
  </React.StrictMode>,
)
