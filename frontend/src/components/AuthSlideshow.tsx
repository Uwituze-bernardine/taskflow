import { useEffect, useState } from 'react'
import loginSlideOne from '../assets/login-slide-1.jpg'
import loginSlideTwo from '../assets/login-slide-2.jpg'

const slides = [loginSlideOne, loginSlideTwo]

export default function AuthSlideshow() {
  const [activeSlide, setActiveSlide] = useState(0)

  useEffect(() => {
    const interval = window.setInterval(() => {
      setActiveSlide((current) => (current + 1) % slides.length)
    }, 6000)
    return () => window.clearInterval(interval)
  }, [])

  return (
    <div className="auth-slideshow" aria-hidden="true">
      {slides.map((image, index) => (
        <img
          key={image}
          className={`auth-slide ${index === activeSlide ? 'active' : ''}`}
          src={image}
          alt=""
        />
      ))}
    </div>
  )
}
