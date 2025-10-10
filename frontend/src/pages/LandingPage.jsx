import React from 'react';
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
  Avatar
} from '@mui/material';
import {
  Chat,
  Description,
  Security,
  Speed,
  School,
  AccountBalance
} from '@mui/icons-material';

const LandingPage = () => {
  const navigate = useNavigate();

  const features = [
    {
      icon: <Chat sx={{ fontSize: 40 }} />,
      title: 'AI-Powered Chat',
      description: 'Get instant answers to your tax questions with our intelligent assistant trained on non-resident tax rules.'
    },
    {
      icon: <Description sx={{ fontSize: 40 }} />,
      title: 'Document Processing',
      description: 'Upload your W-2s, 1099s, and other tax documents. Our OCR technology extracts data automatically.'
    },
    {
      icon: <Security sx={{ fontSize: 40 }} />,
      title: 'Secure & Compliant',
      description: 'Bank-level encryption and IRS compliance. Your data is protected with enterprise-grade security.'
    },
    {
      icon: <Speed sx={{ fontSize: 40 }} />,
      title: 'Fast Processing',
      description: 'Complete your tax return in minutes, not hours. Automated calculations and instant validation.'
    },
    {
      icon: <School sx={{ fontSize: 40 }} />,
      title: 'Expert Knowledge',
      description: 'Built specifically for H1B, F-1, O-1, OPT, J-1, TN, and E-2 visa holders.'
    },
    {
      icon: <AccountBalance sx={{ fontSize: 40 }} />,
      title: 'IRS Forms',
      description: 'Generate 1040NR, W-8BEN, 8843, and 1040-V forms with human review and approval.'
    }
  ];

  return (
    <Box>
      {/* Hero Section */}
      <Box
        sx={{
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          color: 'white',
          py: 10,
          textAlign: 'center'
        }}
      >
        <Container maxWidth="lg">
          <Typography
            variant="h2"
            component="h1"
            gutterBottom
            sx={{
              fontWeight: 'bold',
              mb: 3,
              fontSize: { xs: '2.5rem', md: '3.5rem' }
            }}
          >
            NRTaxAI
          </Typography>
          <Typography
            variant="h4"
            component="h2"
            gutterBottom
            sx={{
              mb: 4,
              opacity: 0.9,
              fontSize: { xs: '1.5rem', md: '2rem' }
            }}
          >
            AI-Powered Tax Preparation for Non-Residents
          </Typography>
          <Typography
            variant="h6"
            component="p"
            sx={{
              mb: 6,
              opacity: 0.8,
              maxWidth: '600px',
              mx: 'auto',
              lineHeight: 1.6
            }}
          >
            Streamline your tax filing process with our intelligent assistant designed 
            specifically for H1B, F-1, O-1, OPT, J-1, TN, and E-2 visa holders.
          </Typography>
          <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center', flexWrap: 'wrap' }}>
            <Button
              variant="contained"
              size="large"
              onClick={() => navigate('/register')}
              sx={{
                bgcolor: 'white',
                color: 'primary.main',
                px: 4,
                py: 1.5,
                fontSize: '1.1rem',
                '&:hover': {
                  bgcolor: 'grey.100'
                }
              }}
            >
              Get Started Free
            </Button>
            <Button
              variant="outlined"
              size="large"
              onClick={() => navigate('/login')}
              sx={{
                borderColor: 'white',
                color: 'white',
                px: 4,
                py: 1.5,
                fontSize: '1.1rem',
                '&:hover': {
                  borderColor: 'white',
                  backgroundColor: 'rgba(255,255,255,0.1)'
                }
              }}
            >
              Login
            </Button>
          </Box>
        </Container>
      </Box>

      {/* Features Section */}
      <Container maxWidth="lg" sx={{ py: 8 }}>
        <Typography
          variant="h3"
          component="h2"
          textAlign="center"
          gutterBottom
          sx={{ mb: 6, fontWeight: 'bold' }}
        >
          Why Choose NRTaxAI?
        </Typography>
        <Grid container spacing={4}>
          {features.map((feature, index) => (
            <Grid item xs={12} md={6} lg={4} key={index}>
              <Card
                sx={{
                  height: '100%',
                  display: 'flex',
                  flexDirection: 'column',
                  transition: 'transform 0.2s ease-in-out',
                  '&:hover': {
                    transform: 'translateY(-4px)',
                    boxShadow: 3
                  }
                }}
              >
                <CardContent sx={{ flexGrow: 1, textAlign: 'center', p: 3 }}>
                  <Avatar
                    sx={{
                      width: 80,
                      height: 80,
                      mx: 'auto',
                      mb: 2,
                      bgcolor: 'primary.main',
                      color: 'white'
                    }}
                  >
                    {feature.icon}
                  </Avatar>
                  <Typography
                    variant="h5"
                    component="h3"
                    gutterBottom
                    sx={{ fontWeight: 'bold', mb: 2 }}
                  >
                    {feature.title}
                  </Typography>
                  <Typography
                    variant="body1"
                    color="text.secondary"
                    sx={{ lineHeight: 1.6 }}
                  >
                    {feature.description}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      </Container>

      {/* CTA Section */}
      <Box
        sx={{
          bgcolor: 'grey.50',
          py: 8,
          textAlign: 'center'
        }}
      >
        <Container maxWidth="md">
          <Typography
            variant="h3"
            component="h2"
            gutterBottom
            sx={{ mb: 3, fontWeight: 'bold' }}
          >
            Ready to Simplify Your Tax Filing?
          </Typography>
          <Typography
            variant="h6"
            color="text.secondary"
            sx={{ mb: 4, lineHeight: 1.6 }}
          >
            Join thousands of non-residents who trust NRTaxAI for their tax preparation needs.
            Start your return today and experience the future of tax filing.
          </Typography>
          <Button
            variant="contained"
            size="large"
            onClick={() => navigate('/register')}
            sx={{
              px: 6,
              py: 2,
              fontSize: '1.2rem',
              fontWeight: 'bold'
            }}
          >
            Start Your Tax Return
          </Button>
        </Container>
      </Box>

      {/* Footer */}
      <Box
        sx={{
          bgcolor: 'primary.main',
          color: 'white',
          py: 4,
          textAlign: 'center'
        }}
      >
        <Container maxWidth="lg">
          <Typography variant="body2" sx={{ opacity: 0.8 }}>
            © 2024 NRTaxAI. All rights reserved. | Secure • Compliant • Trusted
          </Typography>
        </Container>
      </Box>
    </Box>
  );
};

export default LandingPage;
