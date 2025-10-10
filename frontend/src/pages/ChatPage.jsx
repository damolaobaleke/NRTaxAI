import React from 'react';
import { Container, Typography, Paper, Box } from '@mui/material';
import { Chat } from '@mui/icons-material';

const ChatPage = () => {
  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      <Typography variant="h4" component="h1" gutterBottom sx={{ fontWeight: 'bold' }}>
        AI Tax Assistant
      </Typography>
      
      <Paper sx={{ p: 4, textAlign: 'center', mt: 4 }}>
        <Chat sx={{ fontSize: 64, color: 'primary.main', mb: 2 }} />
        <Typography variant="h5" gutterBottom>
          Chat Interface Coming Soon
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Our AI-powered chat assistant will help you with your tax questions and guide you through the filing process.
        </Typography>
      </Paper>
    </Container>
  );
};

export default ChatPage;
