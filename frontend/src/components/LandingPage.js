import React, { useState } from 'react';
import {
  Box,
  Typography,
  Button,
  Container,
  Grid,
  Stack,
  styled,
  Link,
} from '@mui/material';
import { useTheme } from '@mui/material/styles';
import { FaRobot, FaShieldAlt, FaMap, FaCogs } from 'react-icons/fa';

const StyledBackground = styled(Box)(({ theme }) => ({
  minHeight: '100vh',
  width: '100vw',
  background: '#fff',
  padding: 0,
  margin: 0,
  boxSizing: 'border-box',
}));

const Navbar = styled(Box, {
  shouldForwardProp: (prop) => prop !== 'scrolled',
})(({ theme, scrolled }) => ({
  position: 'sticky',
  top: 0,
  left: 0,
  right: 0,
  width: '100%',
  display: 'flex',
  justifyContent: 'center',
  alignItems: 'center',
  padding: '24px 40px 10px 40px',
  background: scrolled ? 'rgba(255,255,255,0.85)' : 'transparent',
  boxShadow: scrolled ? '0 2px 16px rgba(0,0,0,0.04)' : 'none',
  backdropFilter: scrolled ? 'blur(8px)' : 'none',
  transition: 'background 0.3s, box-shadow 0.3s, backdrop-filter 0.3s',
  zIndex: 1100,
  [theme.breakpoints.down('sm')]: {
    flexDirection: 'column',
    alignItems: 'center',
    padding: '16px 16px 0 16px',
  },
}));

const NavLinks = styled(Stack)(({ theme }) => ({
  flexDirection: 'row',
  gap: '32px',
  alignItems: 'center',
  [theme.breakpoints.down('sm')]: {
    gap: '16px',
  },
}));

const FeatureCard = styled(Box)(({ theme }) => ({
  background: '#fff',
  border: '1px solid #e5e7eb',
  borderRadius: '16px',
  boxShadow: '0 2px 8px rgba(0,0,0,0.03)',
  padding: theme.spacing(4, 3),
  textAlign: 'center',
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  height: '100%',
}));

const FeatureSection = styled(Box)(({ theme }) => ({
  marginTop: theme.spacing(8),
  width: '100%',
  maxWidth: 1200,
  margin: '0 auto',
  padding: theme.spacing(4),
}));

const LandingPage = () => {
  const [email, setEmail] = useState('');
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState(false);
  const theme = useTheme();
  const [navScrolled, setNavScrolled] = useState(false);

  // Sticky/translucent navbar effect
  React.useEffect(() => {
    const handleScroll = () => {
      setNavScrolled(window.scrollY > 24);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      // TODO: Implement actual form submission to your backend
      console.log('Submitting email:', email);
      setSuccess(true);
      setError(false);
      setEmail('');
    } catch (err) {
      setError(true);
      setSuccess(false);
    }
  };

  return (
    <StyledBackground>
      {/* Navbar */}
      <Navbar scrolled={navScrolled ? 1 : 0}>
        {/* <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <img src="./nrtaxai-logo.png" alt="NRTax.AI Logo" style={{ height: 38, marginRight: 12, display: 'block' }} />
        </Box> */}
        <Box sx={{ width: 38, height: 38, bgcolor: '#031c2b', borderRadius: '50%', mr: 1 }} />
          <Typography variant="h6" sx={{ color: '#031c2b', fontWeight: 800, letterSpacing: 1 }}>
            NRTax.AI
          </Typography>
        <NavLinks>
          <Link href="#" underline="none" sx={{ color: '#031c2b', fontWeight: 500, mx: 1, border: '1px solid transparent', px: 1, py: 1, borderRadius: 2, transition: 'border 0.2s', '&:hover': { border: '1px solid #031c2b', bgcolor: 'transparent', } }}>Features</Link>
          <Link href="#" underline="none" sx={{ color: '#031c2b', fontWeight: 500, mx: 1, border: '1px solid transparent', px: 1, py: 1, borderRadius: 2, transition: 'border 0.2s', '&:hover': { border: '1px solid #031c2b', bgcolor: 'transparent', } }}>Pricing</Link>
          <Link href="#" underline="none" sx={{ color: '#031c2b', fontWeight: 500, mx: 1, border: '1px solid transparent', px: 1, py: 1, borderRadius: 2, transition: 'border 0.2s', '&:hover': { border: '1px solid #031c2b', bgcolor: 'transparent', } }}>Get in Touch</Link>
          <Button variant="contained" sx={{ bgcolor: '#031c2b', color: '#fff', borderRadius: 4, px: 3, boxShadow: 1, '&:hover': { bgcolor: '#052c49' } }}>
            Sign In
          </Button>
        </NavLinks>
      </Navbar>

      {/* Hero Section */}
      <Box sx={{ pt: { xs: 8, md: 12 }, pb: { xs: 6, md: 10 }, textAlign: 'center', maxWidth: 800, mx: 'auto' }}>
        <Typography variant="h2" sx={{ fontWeight: 700, fontSize: { xs: '2.2rem', md: '3.2rem' }, color: '#031c2b', mb: 2 }}>
          File your Non-Resident Tax Return with <Box component="span" sx={{ color: '#e6007a' }}>ease</Box>
        </Typography>
        <Typography variant="h5" sx={{ color: '#031c2b', opacity: 0.7, mb: 4 }}>
          NRTax.AI is an AI Powered Tax Advisor and Filer for Non-Residents in the U.S.
        </Typography>
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} justifyContent="center" sx={{ mb: 3 }}>
          <Button variant="contained" sx={{ textTransform: 'none', bgcolor: '#031c2b', color: '#fff', px: 4, py: 1.5, fontWeight: 600, borderRadius: 4, fontSize: '1.1rem', '&:hover': { bgcolor: '#052c49' } }}>
            Try NRTax.AI Now
          </Button>
        </Stack>
      </Box>

      {/* Feature Section */}
      <Box sx={{ width: '100%', bgcolor: '#f9fafb', py: { xs: 6, md: 10 } }}>
        <Container maxWidth="lg">
          <Typography variant="h4" sx={{ color: '#031c2b', fontWeight: 700, mb: 2, textAlign: 'center' }}>
            Why use NRTax.AI?
          </Typography>
          <Typography variant="body1" sx={{ color: '#031c2b', opacity: 0.7, mb: 5, textAlign: 'center', maxWidth: 700, mx: 'auto' }}>
            NRTax.AI handles your non-resident tax filing from start to finish so you can focus on what matters.
          </Typography>
          <Grid container spacing={3} justifyContent="center">
            <Grid item xs={12} sm={6} md={3}>
              <FeatureCard>
                <FaMap size={38} color="#031c2b" style={{ marginBottom: 16 }} />
                <Typography variant="h6" sx={{ color: '#031c2b', fontWeight: 700, mb: 1 }}>
                  Auto-maps Your Journey
                </Typography>
                <Typography variant="body2" sx={{ color: '#031c2b', opacity: 0.7 }}>
                  Auto-maps your intake, documenting every step for full visibility.
                </Typography>
              </FeatureCard>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <FeatureCard>
                <FaRobot size={38} color="#031c2b" style={{ marginBottom: 16 }} />
                <Typography variant="h6" sx={{ color: '#031c2b', fontWeight: 700, mb: 1 }}>
                  AI Speeds Up Planning
                </Typography>
                <Typography variant="body2" sx={{ color: '#031c2b', opacity: 0.7 }}>
                  Speeds up planning by tying every answer to detected tax domains.
                </Typography>
              </FeatureCard>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <FeatureCard>
                <FaCogs size={38} color="#031c2b" style={{ marginBottom: 16 }} />
                <Typography variant="h6" sx={{ color: '#031c2b', fontWeight: 700, mb: 1 }}>
                  Detects & Fixes Blockers
                </Typography>
                <Typography variant="body2" sx={{ color: '#031c2b', opacity: 0.7 }}>
                  Detects and fixes blockers to accurate filing, like missing info or eligibility.
                </Typography>
              </FeatureCard>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <FeatureCard>
                <FaShieldAlt size={38} color="#031c2b" style={{ marginBottom: 16 }} />
                <Typography variant="h6" sx={{ color: '#031c2b', fontWeight: 700, mb: 1 }}>
                  Adapts to Changes
                </Typography>
                <Typography variant="body2" sx={{ color: '#031c2b', opacity: 0.7 }}>
                  Continuously adapts to code and tax law changes, so you stay compliant.
                </Typography>
              </FeatureCard>
            </Grid>
          </Grid>
          <Grid container spacing={3} justifyContent="center" sx={{ mt: 1 }}>
            <Grid item xs={12} sm={6} md={3}>
              <FeatureCard>
                <Box sx={{ mb: 2 }}>
                  <span role="img" aria-label="Chat" style={{ fontSize: 36 }}>💬</span>
                </Box>
                <Typography variant="h6" sx={{ color: '#031c2b', fontWeight: 700, mb: 1 }}>
                  Chat-based AI Guidance
                </Typography>
                <Typography variant="body2" sx={{ color: '#031c2b', opacity: 0.7 }}>
                  Trained on IRS rules for accurate, affordable, and stress-free filing.
                </Typography>
              </FeatureCard>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <FeatureCard>
                <Box sx={{ mb: 2 }}>
                  <span role="img" aria-label="Forms" style={{ fontSize: 36 }}>📝</span>
                </Box>
                <Typography variant="h6" sx={{ color: '#031c2b', fontWeight: 700, mb: 1 }}>
                  Auto-generates Key Forms
                </Typography>
                <Typography variant="body2" sx={{ color: '#031c2b', opacity: 0.7 }}>
                  Instantly generates 1040-NR, 8843, and W-8BEN forms for you.
                </Typography>
              </FeatureCard>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <FeatureCard>
                <Box sx={{ mb: 2 }}>
                  <span role="img" aria-label="Treaty" style={{ fontSize: 36 }}>📑</span>
                </Box>
                <Typography variant="h6" sx={{ color: '#031c2b', fontWeight: 700, mb: 1 }}>
                  Tax Treaty Optimization
                </Typography>
                <Typography variant="body2" sx={{ color: '#031c2b', opacity: 0.7 }}>
                  Optimize treaties, e-file, and track your refund in one place.
                </Typography>
              </FeatureCard>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <FeatureCard>
                <Box sx={{ mb: 2 }}>
                  <span role="img" aria-label="Language" style={{ fontSize: 36 }}>🌐</span>
                </Box>
                <Typography variant="h6" sx={{ color: '#031c2b', fontWeight: 700, mb: 1 }}>
                  Multilingual Assistance
                </Typography>
                <Typography variant="body2" sx={{ color: '#031c2b', opacity: 0.7 }}>
                  Support for foreign students and non-residents in multiple languages.
                </Typography>
              </FeatureCard>
            </Grid>
          </Grid>
        </Container>
      </Box>

      {/* Footer Section */}
      <Box component="footer" sx={{ width: '100%', bgcolor: '#031c2b', color: '#fff', py: 4, mt: 0, mb: 0, borderTop: '1px solid rgba(255, 255, 255, 0.1)', position: 'relative', bottom: 0 }}>
        <Box sx={{ maxWidth: 1200, mx: 'auto', px: 2, display: 'flex', flexDirection: { xs: 'column', md: 'row' }, justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="body2" sx={{ opacity: 0.7, mb: { xs: 2, md: 0 } }}>
            &copy; {new Date().getFullYear()} NRTax.AI. All rights reserved.
          </Typography>
          <Box sx={{ display: 'flex', gap: 3 }}>
            <Link href="#" underline="hover" sx={{ color: '#fff', opacity: 0.8, fontSize: '0.95rem', '&:hover': { color: '#e6007a', opacity: 1 } }}>Privacy Policy</Link>
            <Link href="#" underline="hover" sx={{ color: '#fff', opacity: 0.8, fontSize: '0.95rem', '&:hover': { color: '#e6007a', opacity: 1 } }}>Terms</Link>
            <Link href="#" underline="hover" sx={{ color: '#fff', opacity: 0.8, fontSize: '0.95rem', '&:hover': { color: '#e6007a', opacity: 1 } }}>Contact</Link>
          </Box>
        </Box>
      </Box>
    </StyledBackground>
  );
};

export default LandingPage;
