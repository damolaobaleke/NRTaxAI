import React, { useState, useCallback } from 'react';
import {
  Box,
  Button,
  Typography,
  Paper,
  LinearProgress,
  Alert,
  Chip,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControl,
  InputLabel,
  Select,
  MenuItem
} from '@mui/material';
import {
  CloudUpload,
  Delete,
  CheckCircle,
  Error,
  Warning,
  Visibility
} from '@mui/icons-material';
import { documentService } from '../services/authService';

const DocumentUploader = ({ returnId = null, onUploadComplete }) => {
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [documents, setDocuments] = useState([]);
  const [selectedDocType, setSelectedDocType] = useState('');
  const [previewDialog, setPreviewDialog] = useState({ open: false, document: null });

  const documentTypes = [
    { value: 'W2', label: 'W-2 Wage and Tax Statement' },
    { value: '1099INT', label: '1099-INT Interest Income' },
    { value: '1099NEC', label: '1099-NEC Nonemployee Compensation' },
    { value: '1098T', label: '1098-T Tuition Statement' },
    { value: '1042S', label: '1042-S Foreign Person\'s U.S. Source Income' },
    { value: '1099DIV', label: '1099-DIV Dividends and Distributions' },
    { value: '1099B', label: '1099-B Proceeds from Broker Transactions' },
    { value: '1099MISC', label: '1099-MISC Miscellaneous Income' }
  ];

  const handleFileSelect = useCallback(async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    if (!selectedDocType) {
      setError('Please select a document type first');
      return;
    }

    // Validate file type
    const allowedTypes = ['application/pdf', 'image/png', 'image/jpeg', 'image/jpg'];
    if (!allowedTypes.includes(file.type)) {
      setError('Please select a PDF, PNG, or JPEG file');
      return;
    }

    // Validate file size (10MB limit)
    const maxSize = 10 * 1024 * 1024; // 10MB
    if (file.size > maxSize) {
      setError('File size must be less than 10MB');
      return;
    }

    await uploadDocument(file, selectedDocType);
  }, [selectedDocType, returnId]);

  const uploadDocument = async (file, docType) => {
    setUploading(true);
    setError('');
    setSuccess('');
    setUploadProgress(0);

    try {
      // Step 1: Request upload URL
      const uploadData = await documentService.requestUploadUrl(docType, returnId);
      
      // Step 2: Upload file to S3
      const formData = new FormData();
      
      // Add the fields from the presigned POST
      Object.entries(uploadData.fields).forEach(([key, value]) => {
        formData.append(key, value);
      });
      
      // Add the file last
      formData.append('file', file);

      // Upload with progress tracking
      const xhr = new XMLHttpRequest();
      
      xhr.upload.addEventListener('progress', (event) => {
        if (event.lengthComputable) {
          const progress = Math.round((event.loaded / event.total) * 100);
          setUploadProgress(progress);
        }
      });

      const uploadPromise = new Promise((resolve, reject) => {
        xhr.onload = () => {
          if (xhr.status === 204) {
            resolve();
          } else {
            reject(new Error('Upload failed'));
          }
        };
        xhr.onerror = () => reject(new Error('Upload failed'));
        xhr.open('POST', uploadData.upload_url);
        xhr.send(formData);
      });

      await uploadPromise;

      // Step 3: Confirm upload and initiate processing
      const confirmResult = await documentService.confirmUpload(uploadData.document_id);

      // Add document to list
      const newDocument = {
        id: uploadData.document_id,
        doc_type: docType,
        status: confirmResult.status,
        file_size: confirmResult.file_size_bytes,
        av_scan_result: confirmResult.av_scan_result,
        created_at: new Date().toISOString()
      };

      setDocuments(prev => [newDocument, ...prev]);
      setSuccess(`Document uploaded successfully! Status: ${confirmResult.status}`);
      
      if (onUploadComplete) {
        onUploadComplete(newDocument);
      }

    } catch (err) {
      setError(`Upload failed: ${err.message}`);
      console.error('Upload error:', err);
    } finally {
      setUploading(false);
      setUploadProgress(0);
    }
  };

  const deleteDocument = async (documentId) => {
    try {
      await documentService.deleteDocument(documentId);
      setDocuments(prev => prev.filter(doc => doc.id !== documentId));
      setSuccess('Document deleted successfully');
    } catch (err) {
      setError(`Delete failed: ${err.message}`);
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'clean':
        return <CheckCircle color="success" />;
      case 'quarantined':
        return <Error color="error" />;
      case 'uploading':
        return <LinearProgress />;
      default:
        return <Warning color="warning" />;
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'clean':
        return 'success';
      case 'quarantined':
        return 'error';
      case 'uploading':
        return 'info';
      default:
        return 'warning';
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <Box>
      <Typography variant="h6" gutterBottom>
        Upload Tax Documents
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>
          {error}
        </Alert>
      )}

      {success && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess('')}>
          {success}
        </Alert>
      )}

      {/* Document Type Selection */}
      <FormControl fullWidth sx={{ mb: 2 }}>
        <InputLabel>Document Type</InputLabel>
        <Select
          value={selectedDocType}
          label="Document Type"
          onChange={(e) => setSelectedDocType(e.target.value)}
        >
          {documentTypes.map((type) => (
            <MenuItem key={type.value} value={type.value}>
              {type.label}
            </MenuItem>
          ))}
        </Select>
      </FormControl>

      {/* File Upload */}
      <Paper
        sx={{
          p: 3,
          textAlign: 'center',
          border: '2px dashed',
          borderColor: 'primary.main',
          mb: 3,
          cursor: uploading ? 'not-allowed' : 'pointer',
          opacity: uploading ? 0.6 : 1
        }}
      >
        <input
          type="file"
          accept=".pdf,.png,.jpg,.jpeg"
          onChange={handleFileSelect}
          disabled={uploading || !selectedDocType}
          style={{ display: 'none' }}
          id="file-upload"
        />
        <label htmlFor="file-upload">
          <Box sx={{ cursor: 'pointer' }}>
            <CloudUpload sx={{ fontSize: 48, color: 'primary.main', mb: 1 }} />
            <Typography variant="h6" gutterBottom>
              {uploading ? 'Uploading...' : 'Click to upload or drag and drop'}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              PDF, PNG, or JPEG files up to 10MB
            </Typography>
          </Box>
        </label>

        {uploading && (
          <Box sx={{ mt: 2 }}>
            <LinearProgress 
              variant="determinate" 
              value={uploadProgress} 
              sx={{ mb: 1 }}
            />
            <Typography variant="body2">
              {uploadProgress}% uploaded
            </Typography>
          </Box>
        )}
      </Paper>

      {/* Uploaded Documents */}
      {documents.length > 0 && (
        <Box>
          <Typography variant="h6" gutterBottom>
            Uploaded Documents
          </Typography>
          {documents.map((doc) => (
            <Paper key={doc.id} sx={{ p: 2, mb: 2 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                {getStatusIcon(doc.status)}
                <Box sx={{ flexGrow: 1 }}>
                  <Typography variant="subtitle1">
                    {documentTypes.find(t => t.value === doc.doc_type)?.label || doc.doc_type}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {formatFileSize(doc.file_size)} • {new Date(doc.created_at).toLocaleDateString()}
                  </Typography>
                </Box>
                <Chip
                  label={doc.status}
                  color={getStatusColor(doc.status)}
                  size="small"
                />
                <IconButton
                  size="small"
                  onClick={() => setPreviewDialog({ open: true, document: doc })}
                >
                  <Visibility />
                </IconButton>
                <IconButton
                  size="small"
                  onClick={() => deleteDocument(doc.id)}
                  color="error"
                >
                  <Delete />
                </IconButton>
              </Box>
            </Paper>
          ))}
        </Box>
      )}

      {/* Document Preview Dialog */}
      <Dialog
        open={previewDialog.open}
        onClose={() => setPreviewDialog({ open: false, document: null })}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          Document Details: {previewDialog.document?.doc_type}
        </DialogTitle>
        <DialogContent>
          {previewDialog.document && (
            <Box>
              <Typography variant="body1" gutterBottom>
                <strong>Status:</strong> {previewDialog.document.status}
              </Typography>
              <Typography variant="body1" gutterBottom>
                <strong>File Size:</strong> {formatFileSize(previewDialog.document.file_size)}
              </Typography>
              <Typography variant="body1" gutterBottom>
                <strong>Upload Date:</strong> {new Date(previewDialog.document.created_at).toLocaleString()}
              </Typography>
              
              {previewDialog.document.av_scan_result && (
                <Box sx={{ mt: 2 }}>
                  <Typography variant="h6" gutterBottom>
                    Security Scan Results
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    <strong>Clean:</strong> {previewDialog.document.av_scan_result.clean ? 'Yes' : 'No'}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    <strong>Threats Detected:</strong> {previewDialog.document.av_scan_result.threats_detected || 0}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    <strong>Scan Engine:</strong> {previewDialog.document.av_scan_result.scan_engine || 'Unknown'}
                  </Typography>
                </Box>
              )}
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPreviewDialog({ open: false, document: null })}>
            Close
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default DocumentUploader;
