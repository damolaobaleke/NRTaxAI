import React from 'react';
import { Container, Typography, Paper, Box } from '@mui/material';
import { AccountCircle } from '@mui/icons-material';

const ProfilePage = () => {
  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      <Typography variant="h4" component="h1" gutterBottom sx={{ fontWeight: 'bold' }}>
        User Profile
      </Typography>
      
      <Paper sx={{ p: 4, textAlign: 'center', mt: 4 }}>
        <AccountCircle sx={{ fontSize: 64, color: 'primary.main', mb: 2 }} />
        <Typography variant="h5" gutterBottom>
          Profile Management Coming Soon
        </Typography>
        <Typography variant="body1" color="text.secondary">
          This page will allow you to manage your personal information, visa status, and tax preferences.
        </Typography>
      </Paper>
    </Container>
  );
};

export default ProfilePage;
