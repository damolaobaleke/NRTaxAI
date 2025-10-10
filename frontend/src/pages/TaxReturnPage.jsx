import React from 'react';
import { useParams } from 'react-router-dom';
import { Container, Typography, Paper, Box } from '@mui/material';
import { Description } from '@mui/icons-material';

const TaxReturnPage = () => {
  const { returnId } = useParams();

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      <Typography variant="h4" component="h1" gutterBottom sx={{ fontWeight: 'bold' }}>
        Tax Return {returnId?.slice(0, 8)}...
      </Typography>
      
      <Paper sx={{ p: 4, textAlign: 'center', mt: 4 }}>
        <Description sx={{ fontSize: 64, color: 'primary.main', mb: 2 }} />
        <Typography variant="h5" gutterBottom>
          Tax Return Interface Coming Soon
        </Typography>
        <Typography variant="body1" color="text.secondary">
          This page will show your tax return details, document uploads, and filing progress.
        </Typography>
      </Paper>
    </Container>
  );
};

export default TaxReturnPage;
