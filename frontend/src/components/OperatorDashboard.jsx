import React, { useState, useEffect } from 'react';
import {
  Box,
  Container,
  Typography,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Button,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Alert,
  Grid,
  Card,
  CardContent,
  Divider,
  List,
  ListItem,
  ListItemText,
  Tab,
  Tabs
} from '@mui/material';
import {
  Visibility,
  CheckCircle,
  Cancel,
  Edit,
  Assessment
} from '@mui/icons-material';
import apiClient from '../services/authService';

const OperatorDashboard = () => {
  const [queue, setQueue] = useState([]);
  const [selectedReturn, setSelectedReturn] = useState(null);
  const [reviewDialogOpen, setReviewDialogOpen] = useState(false);
  const [decision, setDecision] = useState('');
  const [comments, setComments] = useState('');
  const [revisionItems, setRevisionItems] = useState([]);
  const [stats, setStats] = useState(null);
  const [tabValue, setTabValue] = useState(0);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    loadReviewQueue();
    loadOperatorStats();
  }, []);

  const loadReviewQueue = async () => {
    try {
      const response = await apiClient.get('/operators/queue');
      setQueue(response.data.queue || []);
    } catch (err) {
      setError('Failed to load review queue');
      console.error(err);
    }
  };

  const loadOperatorStats = async () => {
    try {
      const response = await apiClient.get('/operators/stats');
      setStats(response.data);
    } catch (err) {
      console.error('Failed to load stats:', err);
    }
  };

  const viewReturn = async (returnId) => {
    try {
      const response = await apiClient.get(`/operators/returns/${returnId}`);
      setSelectedReturn(response.data);
      setReviewDialogOpen(true);
    } catch (err) {
      setError('Failed to load return details');
      console.error(err);
    }
  };

  const submitReview = async () => {
    try {
      if (!selectedReturn || !decision) return;

      const reviewData = {
        decision,
        comments,
        diffs: revisionItems.length > 0 ? { revision_items: revisionItems } : null
      };

      await apiClient.post(
        `/operators/returns/${selectedReturn.return_id}/review`,
        reviewData
      );

      setSuccess(`Return ${decision === 'approved' ? 'approved' : decision === 'rejected' ? 'rejected' : 'sent back for revision'}`);
      setReviewDialogOpen(false);
      setSelectedReturn(null);
      setDecision('');
      setComments('');
      setRevisionItems([]);
      
      // Reload queue
      loadReviewQueue();
      loadOperatorStats();
    } catch (err) {
      setError('Failed to submit review');
      console.error(err);
    }
  };

  const approveReturn = async (returnId) => {
    try {
      await apiClient.post(`/operators/returns/${returnId}/approve`, {
        comments: comments || 'Return approved for filing'
      });

      setSuccess('Return approved! Form 8879 generated for signatures.');
      setReviewDialogOpen(false);
      loadReviewQueue();
      loadOperatorStats();
    } catch (err) {
      setError('Failed to approve return');
      console.error(err);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'review':
        return 'warning';
      case 'approved':
        return 'success';
      case 'rejected':
        return 'error';
      case 'needs_revision':
        return 'info';
      default:
        return 'default';
    }
  };

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      <Typography variant="h4" gutterBottom>
        Operator Dashboard
      </Typography>
      <Typography variant="subtitle1" color="text.secondary" gutterBottom>
        PTIN Holder Review Queue
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

      {/* Operator Stats */}
      {stats && (
        <Grid container spacing={2} sx={{ mb: 4 }}>
          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Typography color="text.secondary" gutterBottom>
                  Pending Review
                </Typography>
                <Typography variant="h4">{stats.pending_review}</Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Typography color="text.secondary" gutterBottom>
                  Total Reviews
                </Typography>
                <Typography variant="h4">{stats.total_reviews}</Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Typography color="text.secondary" gutterBottom>
                  Approved
                </Typography>
                <Typography variant="h4" color="success.main">
                  {stats.approved}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Typography color="text.secondary" gutterBottom>
                  Needs Revision
                </Typography>
                <Typography variant="h4" color="warning.main">
                  {stats.needs_revision}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Review Queue Table */}
      <Paper>
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Return ID</TableCell>
                <TableCell>Taxpayer</TableCell>
                <TableCell>Visa</TableCell>
                <TableCell>Country</TableCell>
                <TableCell>Tax Year</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Documents</TableCell>
                <TableCell>Submitted</TableCell>
                <TableCell>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {queue.map((item) => (
                <TableRow key={item.return_id}>
                  <TableCell>{item.return_id.substring(0, 8)}...</TableCell>
                  <TableCell>
                    {item.taxpayer.first_name} {item.taxpayer.last_name}
                    <br />
                    <Typography variant="caption" color="text.secondary">
                      {item.taxpayer.email}
                    </Typography>
                  </TableCell>
                  <TableCell>{item.taxpayer.visa_class}</TableCell>
                  <TableCell>{item.taxpayer.country}</TableCell>
                  <TableCell>{item.tax_year}</TableCell>
                  <TableCell>
                    <Chip 
                      label={item.status} 
                      color={getStatusColor(item.status)} 
                      size="small" 
                    />
                  </TableCell>
                  <TableCell>{item.document_count} docs</TableCell>
                  <TableCell>
                    {new Date(item.submitted_at).toLocaleDateString()}
                  </TableCell>
                  <TableCell>
                    <Button
                      size="small"
                      variant="outlined"
                      startIcon={<Visibility />}
                      onClick={() => viewReturn(item.return_id)}
                    >
                      Review
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
              {queue.length === 0 && (
                <TableRow>
                  <TableCell colSpan={9} align="center">
                    <Typography color="text.secondary">
                      No returns pending review
                    </Typography>
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>

      {/* Review Dialog */}
      <Dialog
        open={reviewDialogOpen}
        onClose={() => setReviewDialogOpen(false)}
        maxWidth="lg"
        fullWidth
      >
        <DialogTitle>
          Tax Return Review
          {selectedReturn && (
            <Typography variant="subtitle2" color="text.secondary">
              {selectedReturn.taxpayer.first_name} {selectedReturn.taxpayer.last_name} - Tax Year {selectedReturn.tax_year}
            </Typography>
          )}
        </DialogTitle>
        <DialogContent>
          {selectedReturn && (
            <Box>
              <Tabs value={tabValue} onChange={(e, newValue) => setTabValue(newValue)}>
                <Tab label="Summary" />
                <Tab label="Documents" />
                <Tab label="Forms" />
                <Tab label="Computation" />
                <Tab label="History" />
              </Tabs>

              {/* Summary Tab */}
              {tabValue === 0 && (
                <Box sx={{ py: 2 }}>
                  <Typography variant="h6" gutterBottom>
                    Taxpayer Information
                  </Typography>
                  <Grid container spacing={2}>
                    <Grid item xs={6}>
                      <Typography variant="body2">
                        <strong>Name:</strong> {selectedReturn.taxpayer.first_name} {selectedReturn.taxpayer.last_name}
                      </Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="body2">
                        <strong>Email:</strong> {selectedReturn.taxpayer.email}
                      </Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="body2">
                        <strong>Visa:</strong> {selectedReturn.taxpayer.visa_class}
                      </Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="body2">
                        <strong>Country:</strong> {selectedReturn.taxpayer.country}
                      </Typography>
                    </Grid>
                  </Grid>

                  <Divider sx={{ my: 2 }} />

                  <Typography variant="h6" gutterBottom>
                    Tax Summary
                  </Typography>
                  <Grid container spacing={2}>
                    <Grid item xs={6}>
                      <Typography variant="body2">
                        <strong>Residency Status:</strong> {selectedReturn.computation.residency_determination?.residency_status || 'N/A'}
                      </Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="body2">
                        <strong>Ruleset Version:</strong> {selectedReturn.ruleset_version || 'N/A'}
                      </Typography>
                    </Grid>
                  </Grid>
                </Box>
              )}

              {/* Documents Tab */}
              {tabValue === 1 && (
                <Box sx={{ py: 2 }}>
                  <List>
                    {selectedReturn.documents.map((doc) => (
                      <ListItem key={doc.id}>
                        <ListItemText
                          primary={`${doc.type} - ${doc.status}`}
                          secondary={`Uploaded: ${new Date(doc.uploaded_at).toLocaleString()}`}
                        />
                        <Chip label={doc.status} size="small" />
                      </ListItem>
                    ))}
                  </List>
                </Box>
              )}

              {/* Forms Tab */}
              {tabValue === 2 && (
                <Box sx={{ py: 2 }}>
                  <List>
                    {selectedReturn.forms.map((form) => (
                      <ListItem key={form.id}>
                        <ListItemText
                          primary={`Form ${form.type}`}
                          secondary={`Generated: ${new Date(form.generated_at).toLocaleString()}`}
                        />
                        <Button size="small" variant="outlined">
                          Download
                        </Button>
                      </ListItem>
                    ))}
                  </List>
                </Box>
              )}

              {/* Computation Tab */}
              {tabValue === 3 && (
                <Box sx={{ py: 2 }}>
                  <Typography variant="body2">
                    <strong>Tax Computation:</strong>
                  </Typography>
                  <pre style={{ fontSize: '12px', overflow: 'auto' }}>
                    {JSON.stringify(selectedReturn.computation, null, 2)}
                  </pre>
                </Box>
              )}

              {/* History Tab */}
              {tabValue === 4 && (
                <Box sx={{ py: 2 }}>
                  <Typography variant="h6" gutterBottom>
                    Previous Reviews
                  </Typography>
                  {selectedReturn.previous_reviews.length === 0 ? (
                    <Typography color="text.secondary">No previous reviews</Typography>
                  ) : (
                    <List>
                      {selectedReturn.previous_reviews.map((review) => (
                        <ListItem key={review.id}>
                          <ListItemText
                            primary={`${review.decision.toUpperCase()} by ${review.reviewer.email}`}
                            secondary={
                              <>
                                {review.comments}
                                <br />
                                {new Date(review.reviewed_at).toLocaleString()}
                              </>
                            }
                          />
                        </ListItem>
                      ))}
                    </List>
                  )}
                </Box>
              )}
            </Box>
          )}

          <Divider sx={{ my: 3 }} />

          {/* Review Decision */}
          <Box>
            <Typography variant="h6" gutterBottom>
              Review Decision
            </Typography>
            
            <TextField
              fullWidth
              multiline
              rows={4}
              label="Comments"
              value={comments}
              onChange={(e) => setComments(e.target.value)}
              sx={{ mb: 2 }}
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setReviewDialogOpen(false)}>
            Cancel
          </Button>
          <Button
            variant="contained"
            color="error"
            startIcon={<Cancel />}
            onClick={() => {
              setDecision('rejected');
              submitReview();
            }}
          >
            Reject
          </Button>
          <Button
            variant="contained"
            color="warning"
            startIcon={<Edit />}
            onClick={() => {
              setDecision('needs_revision');
              submitReview();
            }}
          >
            Request Revision
          </Button>
          <Button
            variant="contained"
            color="success"
            startIcon={<CheckCircle />}
            onClick={() => {
              if (selectedReturn) {
                approveReturn(selectedReturn.return_id);
              }
            }}
          >
            Approve & Generate 8879
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default OperatorDashboard;
