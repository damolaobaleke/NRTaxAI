import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Container,
  Typography,
  Paper,
  Box,
  Grid,
  Card,
  CardContent,
  CardActions,
  Button,
  Chip,
  LinearProgress,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  ListItemSecondaryAction,
  IconButton,
  Divider,
  Tabs,
  Tab,
  Stepper,
  Step,
  StepLabel,
  StepContent,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  CircularProgress,
  Tooltip
} from '@mui/material';
import {
  Description,
  Upload,
  Calculate,
  Receipt,
  CheckCircle,
  Error,
  Warning,
  Info,
  Download,
  Delete,
  Edit,
  Add,
  Visibility,
  FileUpload,
  AttachMoney,
  Assessment,
  Description as FormIcon,
  CloudUpload,
  Refresh,
  Save,
  Send,
  Print,
  Share
} from '@mui/icons-material';
import { documentService, taxReturnService } from '../services/apiService';
import { useAuth } from '../contexts/AuthContext';

const TaxReturnPage = () => {
  const { returnId } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  
  const [taxReturn, setTaxReturn] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [forms, setForms] = useState([]);
  const [validations, setValidations] = useState([]);
  const [computations, setComputations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState(0);
  const [uploadDialog, setUploadDialog] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isUploading, setIsUploading] = useState(false);
  const [activeStep, setActiveStep] = useState(0);

  useEffect(() => {
    if (returnId) {
      loadTaxReturnData();
    }
  }, [returnId]);

  const loadTaxReturnData = async () => {
    try {
      setLoading(true);
      const [returnData, docs, formsData, validationsData, computationsData] = await Promise.all([
        taxReturnService.getTaxReturn(returnId),
        // documentService.getDocuments(returnId),
        taxReturnService.getTaxReturnSummary(returnId),
        // Add more API calls as needed
      ]);

      setTaxReturn(returnData);
      setDocuments(docs.documents || []);
      setForms(formsData?.forms || []);
      setValidations(validationsData?.validations || []);
      setComputations(computationsData?.computations || []);
    } catch (error) {
      console.error('Failed to load tax return data:', error);
      setError('Failed to load tax return data');
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async () => {
    if (!selectedFile) return;

    try {
      setIsUploading(true);
      setUploadProgress(0);

      // Simulate upload progress
      const progressInterval = setInterval(() => {
        setUploadProgress(prev => {
          if (prev >= 90) {
            clearInterval(progressInterval);
            return 90;
          }
          return prev + 10;
        });
      }, 200);

      const uploadUrl = await documentService.requestUploadUrl(
        selectedFile.type,
        returnId
      );

      // Simulate file upload
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      setUploadProgress(100);
      clearInterval(progressInterval);

      // Confirm upload
      await documentService.confirmUpload(uploadUrl.document_id);
      
      setUploadDialog(false);
      setSelectedFile(null);
      setUploadProgress(0);
      loadTaxReturnData(); // Refresh data
    } catch (error) {
      console.error('Upload failed:', error);
      setError('Failed to upload document');
    } finally {
      setIsUploading(false);
    }
  };

  const handleComputeTax = async () => {
    try {
      setLoading(true);
      await taxReturnService.computeTax(returnId);
      loadTaxReturnData(); // Refresh data
    } catch (error) {
      console.error('Tax computation failed:', error);
      setError('Failed to compute tax');
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'completed':
      case 'valid':
        return 'success';
      case 'processing':
      case 'pending':
        return 'warning';
      case 'error':
      case 'invalid':
        return 'error';
      default:
        return 'default';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'completed':
      case 'valid':
        return <CheckCircle />;
      case 'processing':
      case 'pending':
        return <Warning />;
      case 'error':
      case 'invalid':
        return <Error />;
      default:
        return <Info />;
    }
  };

  const renderOverview = () => (
    <Grid container spacing={3}>
      {/* Tax Return Summary */}
      <Grid item xs={12} md={6}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Tax Return Summary
            </Typography>
            <Box sx={{ mb: 2 }}>
              <Typography variant="body2" color="text.secondary">
                Tax Year: {taxReturn?.tax_year}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Status: 
                <Chip 
                  label={taxReturn?.status} 
                  color={getStatusColor(taxReturn?.status)}
                  size="small" 
                  sx={{ ml: 1 }}
                />
              </Typography>
            </Box>
            
            {computations.length > 0 && (
              <Box>
                <Typography variant="subtitle2" gutterBottom>
                  Financial Summary
                </Typography>
                <Table size="small">
                  <TableBody>
                    <TableRow>
                      <TableCell>Total Income</TableCell>
                      <TableCell align="right">
                        ${computations.reduce((sum, comp) => 
                          comp.line_code.startsWith('income') ? sum + comp.amount : sum, 0
                        ).toLocaleString()}
                      </TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell>Total Tax</TableCell>
                      <TableCell align="right">
                        ${computations.reduce((sum, comp) => 
                          comp.line_code.startsWith('tax') ? sum + comp.amount : sum, 0
                        ).toLocaleString()}
                      </TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell>Withholding</TableCell>
                      <TableCell align="right">
                        ${computations.reduce((sum, comp) => 
                          comp.line_code.startsWith('withholding') ? sum + comp.amount : sum, 0
                        ).toLocaleString()}
                      </TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
              </Box>
            )}
          </CardContent>
          <CardActions>
            <Button 
              startIcon={<Calculate />} 
              onClick={handleComputeTax}
              disabled={loading}
            >
              Compute Tax
            </Button>
            <Button startIcon={<Refresh />} onClick={loadTaxReturnData}>
              Refresh
            </Button>
          </CardActions>
        </Card>
      </Grid>

      {/* Progress Tracking */}
      <Grid item xs={12} md={6}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Filing Progress
            </Typography>
            <Stepper activeStep={activeStep} orientation="vertical">
              <Step>
                <StepLabel>Document Upload</StepLabel>
                <StepContent>
                  <Typography variant="body2">
                    Upload required tax documents (W-2, 1099, etc.)
                  </Typography>
                </StepContent>
              </Step>
              <Step>
                <StepLabel>Data Extraction</StepLabel>
                <StepContent>
                  <Typography variant="body2">
                    AI extracts data from uploaded documents
                  </Typography>
                </StepContent>
              </Step>
              <Step>
                <StepLabel>Tax Calculation</StepLabel>
                <StepContent>
                  <Typography variant="body2">
                    Calculate taxes based on extracted data
                  </Typography>
                </StepContent>
              </Step>
              <Step>
                <StepLabel>Form Generation</StepLabel>
                <StepContent>
                  <Typography variant="body2">
                    Generate required tax forms
                  </Typography>
                </StepContent>
              </Step>
              <Step>
                <StepLabel>Review & File</StepLabel>
                <StepContent>
                  <Typography variant="body2">
                    Review and submit your tax return
                  </Typography>
                </StepContent>
              </Step>
            </Stepper>
          </CardContent>
        </Card>
      </Grid>

      {/* Validation Issues */}
      {validations.length > 0 && (
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Validation Issues
              </Typography>
              <List>
                {validations.map((validation, index) => (
                  <ListItem key={index}>
                    <ListItemIcon>
                      {getStatusIcon(validation.severity)}
                    </ListItemIcon>
                    <ListItemText
                      primary={validation.message}
                      secondary={`Field: ${validation.field} | Code: ${validation.code}`}
                    />
                    <Chip 
                      label={validation.severity} 
                      color={getStatusColor(validation.severity)}
                      size="small"
                    />
                  </ListItem>
                ))}
              </List>
            </CardContent>
          </Card>
        </Grid>
      )}
    </Grid>
  );

  const renderDocuments = () => (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h6">Documents</Typography>
        <Button
          variant="contained"
          startIcon={<Upload />}
          onClick={() => setUploadDialog(true)}
        >
          Upload Document
        </Button>
      </Box>

      <Grid container spacing={2}>
        {documents.map((doc) => (
          <Grid item xs={12} sm={6} md={4} key={doc.id}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <Receipt sx={{ mr: 1, color: 'primary.main' }} />
                  <Typography variant="subtitle1" noWrap>
                    {doc.doc_type}
                  </Typography>
                </Box>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Status: 
                  <Chip 
                    label={doc.status} 
                    color={getStatusColor(doc.status)}
                    size="small" 
                    sx={{ ml: 1 }}
                  />
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Uploaded: {new Date(doc.created_at).toLocaleDateString()}
                </Typography>
              </CardContent>
              <CardActions>
                <IconButton size="small">
                  <Visibility />
                </IconButton>
                <IconButton size="small">
                  <Download />
                </IconButton>
                <IconButton size="small" color="error">
                  <Delete />
                </IconButton>
              </CardActions>
            </Card>
          </Grid>
        ))}
      </Grid>

      {documents.length === 0 && (
        <Paper sx={{ p: 4, textAlign: 'center', mt: 2 }}>
          <CloudUpload sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
          <Typography variant="h6" gutterBottom>
            No Documents Uploaded
          </Typography>
          <Typography variant="body2" color="text.secondary" gutterBottom>
            Upload your tax documents to get started
          </Typography>
          <Button
            variant="contained"
            startIcon={<Upload />}
            onClick={() => setUploadDialog(true)}
            sx={{ mt: 2 }}
          >
            Upload First Document
          </Button>
        </Paper>
      )}
    </Box>
  );

  const renderForms = () => (
    <Box>
      <Typography variant="h6" gutterBottom>
        Generated Forms
      </Typography>
      
      {forms.length > 0 ? (
        <Grid container spacing={2}>
          {forms.map((form) => (
            <Grid item xs={12} sm={6} md={4} key={form.id}>
              <Card>
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                    <FormIcon sx={{ mr: 1, color: 'primary.main' }} />
                    <Typography variant="subtitle1">
                      {form.form_type}
                    </Typography>
                  </Box>
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    Version: {form.version}
                  </Typography>
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    Status: 
                    <Chip 
                      label={form.status} 
                      color={getStatusColor(form.status)}
                      size="small" 
                      sx={{ ml: 1 }}
                    />
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Generated: {new Date(form.created_at).toLocaleDateString()}
                  </Typography>
                </CardContent>
                <CardActions>
                  <Button size="small" startIcon={<Visibility />}>
                    Preview
                  </Button>
                  <Button size="small" startIcon={<Download />}>
                    Download
                  </Button>
                  <Button size="small" startIcon={<Print />}>
                    Print
                  </Button>
                </CardActions>
              </Card>
            </Grid>
          ))}
        </Grid>
      ) : (
        <Paper sx={{ p: 4, textAlign: 'center', mt: 2 }}>
          <FormIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
          <Typography variant="h6" gutterBottom>
            No Forms Generated Yet
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Forms will be generated after tax calculation
          </Typography>
        </Paper>
      )}
    </Box>
  );

  const renderCalculations = () => (
    <Box>
      <Typography variant="h6" gutterBottom>
        Tax Calculations
      </Typography>
      
      {computations.length > 0 ? (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Line Code</TableCell>
                <TableCell>Description</TableCell>
                <TableCell align="right">Amount</TableCell>
                <TableCell>Source</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {computations.map((comp) => (
                <TableRow key={comp.id}>
                  <TableCell>{comp.line_code}</TableCell>
                  <TableCell>{comp.description}</TableCell>
                  <TableCell align="right">
                    ${comp.amount.toLocaleString()}
                  </TableCell>
                  <TableCell>{comp.source}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      ) : (
        <Paper sx={{ p: 4, textAlign: 'center', mt: 2 }}>
          <Calculate sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
          <Typography variant="h6" gutterBottom>
            No Calculations Available
          </Typography>
          <Typography variant="body2" color="text.secondary" gutterBottom>
            Run tax calculation to see detailed breakdown
          </Typography>
          <Button
            variant="contained"
            startIcon={<Calculate />}
            onClick={handleComputeTax}
            disabled={loading}
            sx={{ mt: 2 }}
          >
            Calculate Tax
          </Button>
        </Paper>
      )}
    </Box>
  );

  if (loading) {
    return (
      <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '50vh' }}>
          <CircularProgress size={60} />
        </Box>
      </Container>
    );
  }

  if (error) {
    return (
      <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
        <Alert severity="error" onClose={() => setError(null)}>
          {error}
        </Alert>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ mt: 2, mb: 4 }}>
      {/* Header */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" component="h1" gutterBottom sx={{ fontWeight: 'bold' }}>
          Tax Return {returnId?.slice(0, 8)}...
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Tax Year: {taxReturn?.tax_year} | Status: {taxReturn?.status}
        </Typography>
      </Box>

      {/* Tabs */}
      <Paper sx={{ mb: 3 }}>
        <Tabs value={activeTab} onChange={(e, newValue) => setActiveTab(newValue)}>
          <Tab label="Overview" />
          <Tab label="Documents" />
          <Tab label="Forms" />
          <Tab label="Calculations" />
        </Tabs>
      </Paper>

      {/* Tab Content */}
      <Box sx={{ mt: 3 }}>
        {activeTab === 0 && renderOverview()}
        {activeTab === 1 && renderDocuments()}
        {activeTab === 2 && renderForms()}
        {activeTab === 3 && renderCalculations()}
      </Box>

      {/* Upload Dialog */}
      <Dialog open={uploadDialog} onClose={() => setUploadDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Upload Document</DialogTitle>
        <DialogContent>
          <Box sx={{ mt: 2 }}>
            <FormControl fullWidth sx={{ mb: 2 }}>
              <InputLabel>Document Type</InputLabel>
              <Select
                value={selectedFile?.type || ''}
                onChange={(e) => setSelectedFile({ ...selectedFile, type: e.target.value })}
                label="Document Type"
              >
                <MenuItem value="w2">W-2</MenuItem>
                <MenuItem value="1099">1099</MenuItem>
                <MenuItem value="bank_statement">Bank Statement</MenuItem>
                <MenuItem value="receipt">Receipt</MenuItem>
                <MenuItem value="other">Other</MenuItem>
              </Select>
            </FormControl>
            
            <Box sx={{ border: '2px dashed', borderColor: 'primary.main', p: 3, textAlign: 'center' }}>
              <FileUpload sx={{ fontSize: 48, color: 'primary.main', mb: 1 }} />
              <Typography variant="h6" gutterBottom>
                Drop files here or click to upload
              </Typography>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                Supported formats: PDF, JPG, PNG
              </Typography>
              <Button variant="outlined" sx={{ mt: 1 }}>
                Choose File
              </Button>
            </Box>

            {isUploading && (
              <Box sx={{ mt: 2 }}>
                <Typography variant="body2" gutterBottom>
                  Uploading... {uploadProgress}%
                </Typography>
                <LinearProgress variant="determinate" value={uploadProgress} />
              </Box>
            )}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setUploadDialog(false)}>Cancel</Button>
          <Button 
            onClick={handleFileUpload} 
            variant="contained"
            disabled={!selectedFile || isUploading}
          >
            {isUploading ? 'Uploading...' : 'Upload'}
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default TaxReturnPage;