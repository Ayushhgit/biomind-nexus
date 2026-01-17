import React, { useState, useEffect } from 'react';
import styled, { keyframes } from 'styled-components';
import { login, storeAuth } from '../api/auth';

/**
 * BioMind Nexus Login - "Premium Minimal" Edition
 * * CHANGES:
 * 1. Background Grid: Made darker and more visible (15% opacity).
 * 2. Inputs: Added "Lift & Glow" micro-interaction on focus.
 * 3. Typography: tighter tracking, deeper colors for better readability.
 * 4. Logic: 100% UNTOUCHED (same fields, same handlers).
 */

// ============================================
// Data: Slider Videos
// ============================================
const SLIDES = [
  {
    id: 1,
    video: '/3191572-uhd_3840_2160_25fps.mp4', 
    quote: 'Accelerating\nDiscovery.'
  },
  {
    id: 2,
    video: '/14857153_1920_1080_30fps.mp4',
    quote: 'AI-Driven\nPrecision.'
  }
];

// ============================================
// Animations
// ============================================
const float = keyframes`
  0% { transform: translate(0px, 0px); }
  50% { transform: translate(20px, -20px); }
  100% { transform: translate(0px, 0px); }
`;

const fadeIn = keyframes`
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
`;

const spin = keyframes`
  to { transform: rotate(360deg); }
`;

// ============================================
// Styled Components
// ============================================

const PageContainer = styled.div`
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background-color: #f1f5f9; /* Slightly darker slate for contrast */
  padding: 2rem;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  position: relative;
  overflow: hidden;

  /* UPGRADE: Made Grid More Visible (0.05 -> 0.08 opacity and darker color) */
  background-image: 
    linear-gradient(rgba(71, 85, 105, 0.08) 1px, transparent 1px),
    linear-gradient(90deg, rgba(71, 85, 105, 0.08) 1px, transparent 1px);
  background-size: 32px 32px; /* Tighter grid */

  /* Ambient Orbs - kept subtle */
  &::before {
    content: '';
    position: absolute;
    top: -10%;
    right: -5%;
    width: 600px;
    height: 600px;
    background: radial-gradient(circle, rgba(37, 99, 235, 0.1) 0%, rgba(255, 255, 255, 0) 70%);
    border-radius: 50%;
    filter: blur(80px);
    animation: ${float} 12s ease-in-out infinite;
    z-index: 0;
  }

  &::after {
    content: '';
    position: absolute;
    bottom: -10%;
    left: -5%;
    width: 500px;
    height: 500px;
    background: radial-gradient(circle, rgba(6, 182, 212, 0.1) 0%, rgba(255, 255, 255, 0) 70%);
    border-radius: 50%;
    filter: blur(80px);
    animation: ${float} 15s ease-in-out infinite reverse;
    z-index: 0;
  }

  @media (max-width: 768px) {
    padding: 1rem;
    align-items: flex-start;
  }
`;

const LoginCard = styled.div`
  position: relative;
  z-index: 10;
  display: flex;
  width: 100%;
  max-width: 1100px;
  min-height: 650px;
  background: #ffffff;
  border-radius: 24px;
  /* Premium "Soft Lift" Shadow */
  box-shadow: 
    0 25px 50px -12px rgba(15, 23, 42, 0.15), 
    0 0 0 1px rgba(15, 23, 42, 0.02);
  overflow: hidden;
  animation: ${fadeIn} 0.6s cubic-bezier(0.16, 1, 0.3, 1); /* Custom easing */

  @media (max-width: 900px) {
    flex-direction: column;
    min-height: auto;
  }
`;

// ========================
// Left Side: Video Slider
// ========================
const ImageSection = styled.div`
  flex: 1.1;
  position: relative;
  background-color: #0f172a;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 3.5rem; /* More breathing room */
  color: white;
  overflow: hidden;

  @media (max-width: 900px) {
    min-height: 300px;
    flex: none;
    padding: 2rem;
  }
`;

const SlideContainer = styled.div`
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  opacity: ${props => (props.active ? 1 : 0)};
  transition: opacity 1.2s ease-in-out;
  z-index: 1;

  video {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
    filter: saturate(1.1) contrast(1.1); /* Slight boost to video quality */
  }

  /* Elegant dark overlay */
  &::after {
    content: '';
    position: absolute;
    inset: 0;
    background: linear-gradient(to bottom, rgba(2, 6, 23, 0.3) 0%, rgba(2, 6, 23, 0.8) 100%);
    z-index: 2;
  }
`;

const ContentWrapper = styled.div`
  position: relative;
  z-index: 10;
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
`;

const BrandHeader = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
`;

const Logo = styled.div`
  font-weight: 800;
  font-size: 1.25rem;
  letter-spacing: -0.02em;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  text-shadow: 0 2px 10px rgba(0,0,0,0.5);
`;

const BackLink = styled.a`
  color: rgba(255, 255, 255, 0.9);
  text-decoration: none;
  font-size: 0.85rem;
  font-weight: 600;
  background: rgba(255, 255, 255, 0.1);
  padding: 0.6rem 1rem;
  border-radius: 99px; /* Pill shape */
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  transition: all 0.2s;

  &:hover {
    background: rgba(255, 255, 255, 0.2);
    transform: translateY(-1px);
  }
`;

const QuoteDisplay = styled.div`
  h2 {
    font-size: 3.5rem; /* Larger Impact Font */
    font-weight: 700;
    line-height: 1.05;
    margin-bottom: 2.5rem;
    letter-spacing: -0.04em; /* Tight tracking for modern look */
    white-space: pre-line;
    text-shadow: 0 8px 24px rgba(0,0,0,0.4);
    animation: ${fadeIn} 0.6s ease-out;
  }
`;

const CarouselDots = styled.div`
  display: flex;
  gap: 0.6rem;
  
  button {
    border: none;
    padding: 0;
    width: ${props => props.active ? '3rem' : '0.75rem'}; 
    height: 4px;
    background: ${props => props.active ? 'white' : 'rgba(255, 255, 255, 0.3)'};
    border-radius: 4px;
    cursor: pointer;
    transition: all 0.4s cubic-bezier(0.25, 0.4, 0.25, 1);
    
    &:hover {
      background: rgba(255, 255, 255, 0.8);
    }
  }
`;

// ========================
// Right Side: Form (Redesigned)
// ========================
const FormSection = styled.div`
  flex: 0.9;
  background: #ffffff;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 4.5rem; /* Increased padding */
  
  @media (max-width: 480px) {
    padding: 2.5rem;
  }
`;

const FormContainer = styled.div`
  max-width: 360px;
  width: 100%;
  margin: 0 auto;
`;

const Title = styled.h1`
  font-size: 2.25rem;
  font-weight: 800;
  color: #0f172a; /* Slate 900 */
  margin: 0 0 0.75rem 0;
  letter-spacing: -0.04em; /* Tight tracking */
`;

const Subtitle = styled.p`
  color: #64748b; /* Slate 500 */
  margin-bottom: 3rem;
  font-size: 1rem;
  line-height: 1.5;
  font-weight: 400;

  a {
    color: #2563eb;
    text-decoration: none;
    font-weight: 600;
    transition: color 0.2s;
    &:hover { color: #1d4ed8; }
  }
`;

const FormGroup = styled.div`
  margin-bottom: 1.5rem;
`;

const Label = styled.label`
  display: block;
  font-size: 0.85rem;
  font-weight: 600;
  color: #334155; /* Slate 700 */
  margin-bottom: 0.5rem;
  letter-spacing: -0.01em;
`;

/* UPGRADE: The "Catchy" Input */
const Input = styled.input`
  width: 100%;
  padding: 1rem 1.25rem; /* Chunky padding */
  border-radius: 14px;     /* Smooth corners */
  border: 1px solid #e2e8f0;
  background: #f8fafc;
  font-size: 1rem;
  color: #0f172a;
  
  /* The Magic Interaction */
  transition: all 0.25s cubic-bezier(0.2, 0.8, 0.2, 1);

  &::placeholder {
    color: #94a3b8;
  }

  &:hover {
    background: #ffffff;
    border-color: #cbd5e1;
  }

  &:focus {
    outline: none;
    background: #ffffff;
    border-color: #3b82f6;
    /* Lift Up & Glow Effect */
    transform: translateY(-2px);
    box-shadow: 0 10px 20px -5px rgba(59, 130, 246, 0.15), 0 0 0 4px rgba(59, 130, 246, 0.1);
  }
`;

const CheckboxGroup = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 2.5rem; /* More space before button */
  font-size: 0.875rem;

  div {
    display: flex;
    align-items: center;
    gap: 0.6rem;
  }

  input {
    width: 18px;
    height: 18px;
    accent-color: #2563eb;
    cursor: pointer;
    border-radius: 6px;
  }

  label {
    color: #475569;
    cursor: pointer;
    user-select: none;
    font-weight: 500;
  }

  a {
    color: #2563eb;
    text-decoration: none;
    font-weight: 600;
    &:hover { text-decoration: underline; }
  }
`;

const SubmitButton = styled.button`
  width: 100%;
  padding: 1.1rem;
  /* Premium Gradient */
  background: linear-gradient(135deg, #1e40af 0%, #2563eb 100%);
  color: white;
  border: none;
  border-radius: 14px;
  font-size: 1rem;
  font-weight: 600;
  letter-spacing: 0.01em;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  display: flex;
  justify-content: center;
  align-items: center;
  
  /* Button Shadow */
  box-shadow: 0 4px 6px -1px rgba(37, 99, 235, 0.2), 0 2px 4px -1px rgba(37, 99, 235, 0.1);

  &:hover:not(:disabled) {
    background: linear-gradient(135deg, #1e3a8a 0%, #1d4ed8 100%);
    transform: translateY(-2px);
    box-shadow: 0 12px 20px -5px rgba(37, 99, 235, 0.4);
  }

  &:active:not(:disabled) {
    transform: translateY(0);
  }

  &:disabled {
    opacity: 0.7;
    cursor: not-allowed;
  }
`;

const Spinner = styled.div`
  width: 22px;
  height: 22px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-radius: 50%;
  border-top-color: #fff;
  animation: ${spin} 0.8s linear infinite;
`;

const ErrorBanner = styled.div`
  padding: 1rem;
  margin-bottom: 1.5rem;
  background: #fef2f2;
  border-left: 4px solid #ef4444;
  border-radius: 8px;
  color: #b91c1c;
  font-size: 0.875rem;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  animation: ${fadeIn} 0.3s ease-out;
`;

// ============================================
// Component
// ============================================

export default function LoginPage({ onLoginSuccess }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [currentSlide, setCurrentSlide] = useState(0);

  // Auto-rotate slides
  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentSlide((prev) => (prev + 1) % SLIDES.length);
    }, 8000); 
    return () => clearInterval(timer);
  }, []);

  const activeSlide = SLIDES[currentSlide] || SLIDES[0];

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      const response = await login(email, password);
      storeAuth(response.access_token, response.session_id, response.expires_in);
      onLoginSuccess(response);
    } catch (err) {
      setError(err.message || 'Invalid credentials.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <PageContainer>
      <LoginCard>
        {/* LEFT SIDE: Video Slider */}
        <ImageSection>
          {SLIDES.map((slide, index) => (
            <SlideContainer 
              key={slide.id} 
              active={index === currentSlide} 
            >
              <video 
                src={slide.video} 
                autoPlay 
                loop 
                muted 
                playsInline
                onCanPlay={(e) => { e.target.playbackRate = 0.75; }}
                key={slide.video}
              />
            </SlideContainer>
          ))}

          <ContentWrapper>
            <BrandHeader>
              <Logo>
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M12 22C17.5228 22 22 17.5228 22 12C22 6.47715 17.5228 2 12 2C6.47715 2 2 6.47715 2 12C2 17.5228 6.47715 22 12 22Z" stroke="white" strokeWidth="2.5"/>
                  <path d="M8 12L11 15L16 9" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
                BioMind Nexus
              </Logo>
              <BackLink href="/">Back to website</BackLink>
            </BrandHeader>

            <QuoteDisplay>
              <h2 key={currentSlide}>{activeSlide.quote}</h2>
              
              <div style={{ display: 'flex', gap: '0.6rem' }}>
                {SLIDES.map((_, index) => (
                  <CarouselDots 
                    key={index} 
                    active={index === currentSlide}
                    onClick={() => setCurrentSlide(index)}
                  >
                    <button type="button" aria-label={`Go to slide ${index + 1}`} />
                  </CarouselDots>
                ))}
              </div>
            </QuoteDisplay>
          </ContentWrapper>
        </ImageSection>

        {/* RIGHT SIDE: Form (Premium Redesign) */}
        <FormSection>
          <FormContainer>
            <Title>Welcome back</Title>
            <Subtitle>
              Please enter your details to sign in.
            </Subtitle>

            <form onSubmit={handleSubmit}>
              {error && (
                <ErrorBanner>
                  <svg width="18" height="18" fill="currentColor" viewBox="0 0 16 16">
                    <path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14zm0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16z"/>
                    <path d="M7.002 11a1 1 0 1 1 2 0 1 1 0 0 1-2 0zM7.1 4.995a.905.905 0 1 1 1.8 0l-.35 3.507a.552.552 0 0 1-1.1 0z"/>
                  </svg>
                  {error}
                </ErrorBanner>
              )}

              <FormGroup>
                <Label htmlFor="email">Email Address</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="name@company.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </FormGroup>

              <FormGroup>
                <Label htmlFor="password">Password</Label>
                <Input
                  id="password"
                  type="password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
              </FormGroup>

              <CheckboxGroup>
                <div>
                  <input type="checkbox" id="remember" />
                  <label htmlFor="remember">Remember me</label>
                </div>
                <a href="#">Forgot password?</a>
              </CheckboxGroup>

              <SubmitButton type="submit" disabled={isLoading}>
                {isLoading ? <Spinner /> : "Sign in"}
              </SubmitButton>
            </form>

          </FormContainer>
        </FormSection>
      </LoginCard>
    </PageContainer>
  );
}