import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Container,
  Typography,
  Button,
  Box,
  Grid,
  Card,
  CardContent,
  CardActions,
  Paper,
  Avatar,
  Chip,
  Rating,
  Fade,
  Slide,
  Zoom,
  useTheme,
  useMediaQuery
} from '@mui/material';
import {
  Chat,
  Description,
  Security,
  Speed,
  School,
  AccountBalance,
  CheckCircle,
  Star,
  TrendingUp,
  People,
  Verified,
  AutoAwesome,
  Calculate,
  CloudUpload,
  SupportAgent
} from '@mui/icons-material';

const LandingPage = () => {
  const navigate = useNavigate();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const [currentTestimonial, setCurrentTestimonial] = useState(0);
  const [animatedNumbers, setAnimatedNumbers] = useState({
    users: 0,
    returns: 0,
    accuracy: 0
  });

  // Animate numbers on component mount
  useEffect(() => {
    const animateNumbers = () => {
      const targets = { users: 15000, returns: 50000, accuracy: 99 };
      const duration = 2000;
      const steps = 60;
      const stepDuration = duration / steps;

      let step = 0;
      const timer = setInterval(() => {
        step++;
        const progress = step / steps;
        const easeOut = 1 - Math.pow(1 - progress, 3);

        setAnimatedNumbers({
          users: Math.floor(targets.users * easeOut),
          returns: Math.floor(targets.returns * easeOut),
          accuracy: Math.floor(targets.accuracy * easeOut)
        });

        if (step >= steps) {
          clearInterval(timer);
          setAnimatedNumbers(targets);
        }
      }, stepDuration);

      return () => clearInterval(timer);
    };

    const timer = setTimeout(animateNumbers, 500);
    return () => clearTimeout(timer);
  }, []);

  // Auto-rotate testimonials
  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentTestimonial((prev) => (prev + 1) % testimonials.length);
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  const testimonials = [
    {
      name: "Sarah Chen",
      role: "H1B Software Engineer",
      company: "Google",
      content: "NRTaxAI saved me 8 hours of tax preparation time. The AI assistant understood my complex visa situation perfectly and guided me through every step.",
      rating: 5,
      avatar: "SC"
    },
    {
      name: "Ahmed Hassan",
      role: "F-1 Student",
      company: "Stanford University",
      content: "As an international student, taxes were always confusing. NRTaxAI made it simple and I got my maximum refund. Highly recommended!",
      rating: 5,
      avatar: "AH"
    },
    {
      name: "Priya Patel",
      role: "O-1 Visa Holder",
      company: "Microsoft",
      content: "The document processing feature is incredible. It extracted all my W-2 and 1099 data automatically. This is the future of tax filing.",
      rating: 5,
      avatar: "PP"
    },
    {
      name: "Carlos Rodriguez",
      role: "J-1 Researcher",
      company: "MIT",
      content: "I was worried about making mistakes on my tax return. NRTaxAI's validation caught several issues I would have missed. Peace of mind!",
      rating: 5,
      avatar: "CR"
    }
  ];

  const features = [
    {
      icon: <AutoAwesome sx={{ fontSize: 40 }} />,
      title: 'AI Tax Assistant',
      description: 'Get instant, accurate answers to complex tax questions with our AI trained on millions of tax documents and IRS regulations.',
      color: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
    },
    {
      icon: <CloudUpload sx={{ fontSize: 40 }} />,
      title: 'Smart Document Processing',
      description: 'Upload W-2s, 1099s, and other documents. Our OCR technology extracts data automatically with 99.5% accuracy.',
      color: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)'
    },
    {
      icon: <Security sx={{ fontSize: 40 }} />,
      title: 'Bank-Level Security',
      description: 'Enterprise-grade encryption, SOC 2 compliance, and IRS-approved security standards protect your sensitive data.',
      color: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)'
    },
    {
      icon: <Speed sx={{ fontSize: 40 }} />,
      title: 'Lightning Fast',
      description: 'Complete your entire tax return in under 15 minutes. Automated calculations and instant validation save hours.',
      color: 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)'
    },
    {
      icon: <School sx={{ fontSize: 40 }} />,
      title: 'Visa-Specific Expertise',
      description: 'Built specifically for H1B, F-1, O-1, OPT, J-1, TN, and E-2 visa holders with deep understanding of non-resident tax rules.',
      color: 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)'
    },
    {
      icon: <Calculate sx={{ fontSize: 40 }} />,
      title: 'Automated Form Generation',
      description: 'Generate IRS-compliant 1040NR, W-8BEN, 8843, and 1040-V forms with human review and approval.',
      color: 'linear-gradient(135deg, #a8edea 0%, #fed6e3 100%)'
    }
  ];

  const stats = [
    { label: 'Active Users', value: `${animatedNumbers.users.toLocaleString()}+`, icon: <People /> },
    { label: 'Tax Returns Filed', value: `${animatedNumbers.returns.toLocaleString()}+`, icon: <Description /> },
    { label: 'Accuracy Rate', value: `${animatedNumbers.accuracy}%`, icon: <Verified /> }
  ];

  return (
    <Box>
      {/* Hero Section */}
      <Box
        sx={{
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          color: 'white',
          py: { xs: 8, md: 12 },
          textAlign: 'center',
          position: 'relative',
          overflow: 'hidden'
        }}
      >
        {/* Animated background elements */}
        <Box
          sx={{
            position: 'absolute',
            top: -50,
            right: -50,
            width: 200,
            height: 200,
            borderRadius: '50%',
            background: 'rgba(255,255,255,0.1)',
            animation: 'float 6s ease-in-out infinite'
          }}
        />
        <Box
          sx={{
            position: 'absolute',
            bottom: -30,
            left: -30,
            width: 150,
            height: 150,
            borderRadius: '50%',
            background: 'rgba(255,255,255,0.05)',
            animation: 'float 8s ease-in-out infinite reverse'
          }}
        />

        <Container maxWidth="lg" sx={{ position: 'relative', zIndex: 1 }}>
          <Fade in timeout={1000}>
            <Box>
              <Chip
                label="Trusted by 15,000+ Non-Residents"
                sx={{
                  bgcolor: 'rgba(255,255,255,0.2)',
                  color: 'white',
                  mb: 3,
                  fontSize: '0.9rem',
                  fontWeight: 'bold'
                }}
              />
              <Typography
                variant="h1"
                component="h1"
                gutterBottom
                sx={{
                  fontWeight: 'bold',
                  mb: 3,
                  fontSize: { xs: '2.5rem', md: '4rem' },
                  background: 'linear-gradient(45deg, #fff 30%, #f0f0f0 90%)',
                  backgroundClip: 'text',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent'
                }}
              >
                NRTaxAI
              </Typography>
              <Typography
                variant="h3"
                component="h2"
                gutterBottom
                sx={{
                  mb: 4,
                  opacity: 0.95,
                  fontSize: { xs: '1.5rem', md: '2.2rem' },
                  fontWeight: 600
                }}
              >
                AI-Powered Tax Assistant for Non-Residents
              </Typography>
              <Typography
                variant="h6"
                component="p"
                sx={{
                  mb: 6,
                  opacity: 0.9,
                  maxWidth: '700px',
                  mx: 'auto',
                  lineHeight: 1.7,
                  fontSize: { xs: '1rem', md: '1.2rem' }
                }}
              >
                Get instant, accurate answers to complex tax questions. Complete your entire 
                tax return in under 15 minutes with our AI trained on millions of tax documents.
              </Typography>
              
              {/* Stats */}
              <Box sx={{ mb: 6 }}>
                <Grid container spacing={4} justifyContent="center">
                  {stats.map((stat, index) => (
                    <Grid item xs={12} sm={4} key={index}>
                      <Zoom in timeout={1000 + index * 200}>
                        <Box sx={{ textAlign: 'center' }}>
                          <Typography
                            variant="h3"
                            sx={{
                              fontWeight: 'bold',
                              mb: 1,
                              fontSize: { xs: '2rem', md: '2.5rem' }
                            }}
                          >
                            {stat.value}
                          </Typography>
                          <Typography variant="body1" sx={{ opacity: 0.9 }}>
                            {stat.label}
                          </Typography>
                        </Box>
                      </Zoom>
                    </Grid>
                  ))}
                </Grid>
              </Box>

              <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center', flexWrap: 'wrap' }}>
                <Button
                  variant="contained"
                  size="large"
                  onClick={() => navigate('/register')}
                  sx={{
                    bgcolor: 'white',
                    color: 'primary.main',
                    px: 6,
                    py: 2,
                    fontSize: '1.2rem',
                    fontWeight: 'bold',
                    borderRadius: 3,
                    boxShadow: '0 8px 32px rgba(0,0,0,0.2)',
                    '&:hover': {
                      bgcolor: 'grey.100',
                      transform: 'translateY(-2px)',
                      boxShadow: '0 12px 40px rgba(0,0,0,0.3)'
                    },
                    transition: 'all 0.3s ease'
                  }}
                >
                  Start Free Trial
                </Button>
                <Button
                  variant="outlined"
                  size="large"
                  onClick={() => navigate('/login')}
                  sx={{
                    borderColor: 'white',
                    color: 'white',
                    px: 6,
                    py: 2,
                    fontSize: '1.2rem',
                    fontWeight: 'bold',
                    borderRadius: 3,
                    borderWidth: 2,
                    '&:hover': {
                      borderColor: 'white',
                      backgroundColor: 'rgba(255,255,255,0.1)',
                      borderWidth: 2
                    }
                  }}
                >
                  Sign In
                </Button>
              </Box>
            </Box>
          </Fade>
        </Container>

        {/* Add CSS animation */}
        <style jsx>{`
          @keyframes float {
            0%, 100% { transform: translateY(0px) rotate(0deg); }
            50% { transform: translateY(-20px) rotate(180deg); }
          }
        `}</style>
      </Box>

      {/* Features Section */}
      <Container maxWidth="lg" sx={{ py: 10 }}>
        <Box sx={{ textAlign: 'center', mb: 8 }}>
          <Typography
            variant="h2"
            component="h2"
            gutterBottom
            sx={{ 
              fontWeight: 'bold', 
              mb: 3,
              fontSize: { xs: '2rem', md: '3rem' }
            }}
          >
            Powerful Features
          </Typography>
          <Typography
            variant="h6"
            color="text.secondary"
            sx={{ maxWidth: '600px', mx: 'auto', lineHeight: 1.6 }}
          >
            Everything you need to file your taxes accurately and efficiently
          </Typography>
        </Box>
        
        <Grid container spacing={4}>
          {features.map((feature, index) => (
            <Grid item xs={12} md={6} lg={4} key={index}>
              <Slide direction="up" in timeout={800 + index * 200}>
                <Card
                  sx={{
                    height: '100%',
                    display: 'flex',
                    flexDirection: 'column',
                    borderRadius: 3,
                    overflow: 'hidden',
                    transition: 'all 0.3s ease',
                    border: '1px solid',
                    borderColor: 'grey.200',
                    '&:hover': {
                      transform: 'translateY(-8px)',
                      boxShadow: '0 20px 40px rgba(0,0,0,0.1)',
                      borderColor: 'primary.main'
                    }
                  }}
                >
                  <Box
                    sx={{
                      height: 120,
                      background: feature.color,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      position: 'relative'
                    }}
                  >
                    <Avatar
                      sx={{
                        width: 60,
                        height: 60,
                        bgcolor: 'rgba(255,255,255,0.2)',
                        color: 'white',
                        backdropFilter: 'blur(10px)'
                      }}
                    >
                      {feature.icon}
                    </Avatar>
                    <Box
                      sx={{
                        position: 'absolute',
                        top: 0,
                        left: 0,
                        right: 0,
                        bottom: 0,
                        background: 'linear-gradient(45deg, rgba(255,255,255,0.1) 0%, rgba(255,255,255,0.05) 100%)',
                        pointerEvents: 'none'
                      }}
                    />
                  </Box>
                  <CardContent sx={{ flexGrow: 1, p: 3 }}>
                    <Typography
                      variant="h5"
                      component="h3"
                      gutterBottom
                      sx={{ 
                        fontWeight: 'bold', 
                        mb: 2,
                        color: 'text.primary'
                      }}
                    >
                      {feature.title}
                    </Typography>
                    <Typography
                      variant="body1"
                      color="text.secondary"
                      sx={{ lineHeight: 1.7 }}
                    >
                      {feature.description}
                    </Typography>
                  </CardContent>
                </Card>
              </Slide>
            </Grid>
          ))}
        </Grid>
      </Container>

      {/* Testimonials Section */}
      <Box
        sx={{
          bgcolor: 'grey.50',
          py: 10,
          position: 'relative'
        }}
      >
        <Container maxWidth="lg">
          <Box sx={{ textAlign: 'center', mb: 8 }}>
            <Typography
              variant="h2"
              component="h2"
              gutterBottom
              sx={{ 
                fontWeight: 'bold', 
                mb: 3,
                fontSize: { xs: '2rem', md: '3rem' }
              }}
            >
              Loved by Non-Residents Worldwide
            </Typography>
            <Typography
              variant="h6"
              color="text.secondary"
              sx={{ maxWidth: '600px', mx: 'auto', lineHeight: 1.6 }}
            >
              See what our users say about their experience with NRTaxAI
            </Typography>
          </Box>

          <Box sx={{ position: 'relative', minHeight: 300 }}>
            <Fade key={currentTestimonial} in timeout={500}>
              <Card
                sx={{
                  maxWidth: 800,
                  mx: 'auto',
                  p: 4,
                  borderRadius: 3,
                  boxShadow: '0 8px 32px rgba(0,0,0,0.1)',
                  border: '1px solid',
                  borderColor: 'grey.200'
                }}
              >
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
                  <Avatar
                    sx={{
                      width: 60,
                      height: 60,
                      bgcolor: 'primary.main',
                      color: 'white',
                      mr: 3,
                      fontSize: '1.2rem',
                      fontWeight: 'bold'
                    }}
                  >
                    {testimonials[currentTestimonial].avatar}
                  </Avatar>
                  <Box>
                    <Typography variant="h6" sx={{ fontWeight: 'bold' }}>
                      {testimonials[currentTestimonial].name}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {testimonials[currentTestimonial].role}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {testimonials[currentTestimonial].company}
                    </Typography>
                  </Box>
                  <Box sx={{ ml: 'auto' }}>
                    <Rating value={testimonials[currentTestimonial].rating} readOnly />
                  </Box>
                </Box>
                <Typography
                  variant="body1"
                  sx={{
                    fontSize: '1.1rem',
                    lineHeight: 1.7,
                    fontStyle: 'italic',
                    color: 'text.primary'
                  }}
                >
                  "{testimonials[currentTestimonial].content}"
                </Typography>
              </Card>
            </Fade>

            {/* Testimonial indicators */}
            <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4, gap: 1 }}>
              {testimonials.map((_, index) => (
                <Box
                  key={index}
                  onClick={() => setCurrentTestimonial(index)}
                  sx={{
                    width: 12,
                    height: 12,
                    borderRadius: '50%',
                    bgcolor: index === currentTestimonial ? 'primary.main' : 'grey.300',
                    cursor: 'pointer',
                    transition: 'all 0.3s ease',
                    '&:hover': {
                      bgcolor: index === currentTestimonial ? 'primary.dark' : 'grey.400'
                    }
                  }}
                />
              ))}
            </Box>
          </Box>
        </Container>
      </Box>

      {/* CTA Section */}
      <Box
        sx={{
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          color: 'white',
          py: 10,
          textAlign: 'center',
          position: 'relative',
          overflow: 'hidden'
        }}
      >
        {/* Background pattern */}
        <Box
          sx={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'url("data:image/svg+xml,%3Csvg width="60" height="60" viewBox="0 0 60 60" xmlns="http://www.w3.org/2000/svg"%3E%3Cg fill="none" fill-rule="evenodd"%3E%3Cg fill="%23ffffff" fill-opacity="0.05"%3E%3Ccircle cx="30" cy="30" r="2"/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")',
            opacity: 0.3
          }}
        />
        
        <Container maxWidth="md" sx={{ position: 'relative', zIndex: 1 }}>
          <Zoom in timeout={1000}>
            <Box>
              <Typography
                variant="h2"
                component="h2"
                gutterBottom
                sx={{ 
                  mb: 3, 
                  fontWeight: 'bold',
                  fontSize: { xs: '2rem', md: '3rem' }
                }}
              >
                Ready to Transform Your Tax Experience?
              </Typography>
              <Typography
                variant="h6"
                sx={{ 
                  mb: 6, 
                  lineHeight: 1.7,
                  opacity: 0.95,
                  fontSize: { xs: '1rem', md: '1.2rem' }
                }}
              >
                Join thousands of non-residents who trust NRTaxAI for accurate, 
                fast, and secure tax preparation. Start your free trial today.
              </Typography>
              
              <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center', flexWrap: 'wrap', mb: 4 }}>
                <Button
                  variant="contained"
                  size="large"
                  onClick={() => navigate('/register')}
                  sx={{
                    bgcolor: 'white',
                    color: 'primary.main',
                    px: 6,
                    py: 2,
                    fontSize: '1.2rem',
                    fontWeight: 'bold',
                    borderRadius: 3,
                    boxShadow: '0 8px 32px rgba(0,0,0,0.2)',
                    '&:hover': {
                      bgcolor: 'grey.100',
                      transform: 'translateY(-2px)',
                      boxShadow: '0 12px 40px rgba(0,0,0,0.3)'
                    },
                    transition: 'all 0.3s ease'
                  }}
                >
                  Start Free Trial
                </Button>
                <Button
                  variant="outlined"
                  size="large"
                  onClick={() => navigate('/login')}
                  sx={{
                    borderColor: 'white',
                    color: 'white',
                    px: 6,
                    py: 2,
                    fontSize: '1.2rem',
                    fontWeight: 'bold',
                    borderRadius: 3,
                    borderWidth: 2,
                    '&:hover': {
                      borderColor: 'white',
                      backgroundColor: 'rgba(255,255,255,0.1)',
                      borderWidth: 2
                    }
                  }}
                >
                  Sign In
                </Button>
              </Box>

              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 2, flexWrap: 'wrap' }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <CheckCircle sx={{ fontSize: 20 }} />
                  <Typography variant="body2" sx={{ opacity: 0.9 }}>
                    No credit card required
                  </Typography>
                </Box>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <CheckCircle sx={{ fontSize: 20 }} />
                  <Typography variant="body2" sx={{ opacity: 0.9 }}>
                    14-day free trial
                  </Typography>
                </Box>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <CheckCircle sx={{ fontSize: 20 }} />
                  <Typography variant="body2" sx={{ opacity: 0.9 }}>
                    Cancel anytime
                  </Typography>
                </Box>
              </Box>
            </Box>
          </Zoom>
        </Container>
      </Box>

      {/* Footer */}
      <Box
        sx={{
          bgcolor: 'grey.900',
          color: 'white',
          py: 6,
          textAlign: 'center'
        }}
      >
        <Container maxWidth="lg">
          <Box sx={{ mb: 4 }}>
            <Typography
              variant="h4"
              sx={{
                fontWeight: 'bold',
                mb: 2,
                background: 'linear-gradient(45deg, #fff 30%, #f0f0f0 90%)',
                backgroundClip: 'text',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent'
              }}
            >
              NRTaxAI
            </Typography>
            <Typography variant="body1" sx={{ opacity: 0.8, mb: 3 }}>
              The future of tax preparation for non-residents
            </Typography>
          </Box>
          
          <Box sx={{ display: 'flex', justifyContent: 'center', gap: 4, mb: 4, flexWrap: 'wrap' }}>
            <Typography variant="body2" sx={{ opacity: 0.7 }}>
              Privacy Policy
            </Typography>
            <Typography variant="body2" sx={{ opacity: 0.7 }}>
              Terms of Service
            </Typography>
            <Typography variant="body2" sx={{ opacity: 0.7 }}>
              Security
            </Typography>
            <Typography variant="body2" sx={{ opacity: 0.7 }}>
              Support
            </Typography>
          </Box>
          
          <Typography variant="body2" sx={{ opacity: 0.6 }}>
            © {new Date().getFullYear()} NRTaxAI. All rights reserved. | Secure • Compliant • Trusted by 15,000+ Users
          </Typography>
        </Container>
      </Box>
    </Box>
  );
};

export default LandingPage;
