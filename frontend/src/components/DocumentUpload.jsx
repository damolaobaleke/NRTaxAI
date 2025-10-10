import React from 'react';
import { Container, Typography, Box } from '@mui/material';
import DocumentUploader from './DocumentUploader';

const DocumentUpload = () => {
  const handleUploadComplete = (document) => {
    console.log('Document uploaded:', document);
    // You can add additional logic here, like refreshing a document list
  };

  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Upload Tax Documents
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Upload your tax documents securely. All files are automatically scanned for malware and processed for tax preparation.
        </Typography>
      </Box>
      
      <DocumentUploader onUploadComplete={handleUploadComplete} />
    </Container>
  );
};

export default DocumentUpload;
