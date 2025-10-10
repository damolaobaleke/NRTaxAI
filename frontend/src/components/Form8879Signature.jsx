import React, { useState, useEffect } from 'react';
import {
  Box,
  Container,
  Typography,
  Paper,
  TextField,
  Button,
  Alert,
  Card,
  CardContent,
  Stepper,
  Step,
  StepLabel,
  Divider,
  FormControl,
  InputLabel,
  Select,
  MenuItem
} from '@mui/material';
import {
  CheckCircle,
  Warning,
  Info
} from '@mui/icons-material';
import apiClient from '../services/authService';

const Form8879Signature = ({ authorizationId, onComplete }) => {
  const [authorization, setAuthorization] = useState(null);
  const [pin, setPin] = useState('');
  const [signatureMethod, setSignatureMethod] = useState('e-sign');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    loadAuthorization();
  }, [authorizationId]);

  const loadAuthorization = async () => {
    try {
      const response = await apiClient.get(`/authorizations/${authorizationId}`);
      setAuthorization(response.data);
    } catch (err) {
      setError('Failed to load authorization');
      console.error(err);
    }
  };

  const handleSign = async () => {
    if (!pin || pin.length !== 5) {
      setError('PIN must be exactly 5 digits');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await apiClient.post(
        `/authorizations/${authorizationId}/sign/taxpayer`,
        {
          pin,
          signature_method: signatureMethod
        }
      );

      setSuccess('Form 8879 signed successfully! Awaiting preparer signature.');
      
      if (onComplete) {
        onComplete(response.data);
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to sign form');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const getActiveStep = () => {
    if (!authorization) return 0;
    
    switch (authorization.status) {
      case 'pending':
        return 0;
      case 'user_signed':
        return 1;
      case 'signed':
        return 2;
      default:
        return 0;
    }
  };

  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      <Typography variant="h4" gutterBottom>
        Form 8879 - e-file Signature Authorization
      </Typography>
      <Typography variant="subtitle1" color="text.secondary" gutterBottom>
        IRS e-file Signature Authorization
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

      {/* Progress Stepper */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Stepper activeStep={getActiveStep()}>
          <Step>
            <StepLabel>Taxpayer Signature</StepLabel>
          </Step>
          <Step>
            <StepLabel>Preparer Signature</StepLabel>
          </Step>
          <Step>
            <StepLabel>Ready for e-file</StepLabel>
          </Step>
        </Stepper>
      </Paper>

      {/* Authorization Info */}
      {authorization && (
        <Paper sx={{ p: 3, mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            Authorization Details
          </Typography>
          <Grid container spacing={2}>
            <Grid item xs={6}>
              <Typography variant="body2">
                <strong>Tax Year:</strong> {authorization.tax_year}
              </Typography>
            </Grid>
            <Grid item xs={6}>
              <Typography variant="body2">
                <strong>Status:</strong>{' '}
                <Chip label={authorization.status} size="small" />
              </Typography>
            </Grid>
            <Grid item xs={6}>
              <Typography variant="body2">
                <strong>Taxpayer Signed:</strong>{' '}
                {authorization.taxpayer_signed ? <CheckCircle color="success" /> : <Warning color="warning" />}
              </Typography>
            </Grid>
            <Grid item xs={6}>
              <Typography variant="body2">
                <strong>Preparer Signed:</strong>{' '}
                {authorization.operator_signed ? <CheckCircle color="success" /> : <Warning color="warning" />}
              </Typography>
            </Grid>
          </Grid>
        </Paper>
      )}

      {/* Important Information */}
      <Alert severity="info" sx={{ mb: 3 }} icon={<Info />}>
        <Typography variant="body2" gutterBottom>
          <strong>What is Form 8879?</strong>
        </Typography>
        <Typography variant="body2">
          This form authorizes your tax preparer to electronically file your tax return with the IRS.
          By signing this form, you confirm that you have reviewed your return and authorize its electronic submission.
        </Typography>
      </Alert>

      {/* Signature Section */}
      {authorization && authorization.status === 'pending' && (
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>
            Sign Form 8879
          </Typography>
          
          <Alert severity="warning" sx={{ mb: 3 }}>
            Please review your complete tax return before signing this authorization.
            Once signed, your preparer will add their signature and submit your return to the IRS.
          </Alert>

          <FormControl fullWidth sx={{ mb: 2 }}>
            <InputLabel>Signature Method</InputLabel>
            <Select
              value={signatureMethod}
              label="Signature Method"
              onChange={(e) => setSignatureMethod(e.target.value)}
            >
              <MenuItem value="e-sign">Electronic Signature</MenuItem>
              <MenuItem value="phone">Phone Authorization</MenuItem>
              <MenuItem value="wet-sign">Wet Signature (Mail)</MenuItem>
            </Select>
          </FormControl>

          <TextField
            fullWidth
            label="Enter 5-Digit PIN"
            type="password"
            value={pin}
            onChange={(e) => setPin(e.target.value)}
            helperText="Enter a 5-digit PIN that you will remember. This serves as your electronic signature."
            inputProps={{ maxLength: 5, pattern: '[0-9]*' }}
            sx={{ mb: 3 }}
          />

          <Box sx={{ display: 'flex', gap: 2 }}>
            <Button
              fullWidth
              variant="contained"
              color="primary"
              onClick={handleSign}
              disabled={loading || !pin || pin.length !== 5}
            >
              {loading ? 'Signing...' : 'Sign Form 8879'}
            </Button>
          </Box>
        </Paper>
      )}

      {/* Awaiting Preparer Signature */}
      {authorization && authorization.status === 'user_signed' && (
        <Paper sx={{ p: 3 }}>
          <Alert severity="success" icon={<CheckCircle />}>
            <Typography variant="body1" gutterBottom>
              <strong>You have signed Form 8879</strong>
            </Typography>
            <Typography variant="body2">
              Your tax preparer will now review and add their signature. Once complete, 
              your return will be electronically filed with the IRS.
            </Typography>
          </Alert>
        </Paper>
      )}

      {/* Fully Signed */}
      {authorization && authorization.status === 'signed' && (
        <Paper sx={{ p: 3 }}>
          <Alert severity="success" icon={<CheckCircle />}>
            <Typography variant="body1" gutterBottom>
              <strong>Form 8879 Fully Signed</strong>
            </Typography>
            <Typography variant="body2">
              Both you and your tax preparer have signed Form 8879. 
              Your return is now ready for e-file submission to the IRS.
            </Typography>
          </Alert>
        </Paper>
      )}
    </Container>
  );
};

export default Form8879Signature;
