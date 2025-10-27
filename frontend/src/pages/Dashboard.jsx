import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Container,
  Typography,
  Box,
  Grid,
  Card,
  CardContent,
  CardActions,
  Button,
  Paper,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  Chip,
  Alert
} from '@mui/material';
import {
  Add,
  Chat,
  Description,
  Assessment,
  CheckCircle,
  Warning,
  Info
} from '@mui/icons-material';
import { useAuth } from '../contexts/AuthContext';
import { taxReturnService, chatService } from '../services/authService';

const Dashboard = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [taxReturns, setTaxReturns] = useState([]);
  const [chatSessions, setChatSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      const [returnsData, sessionsData] = await Promise.all([
        taxReturnService.getTaxReturns(),
        chatService.getUserSessions()
      ]);
      setTaxReturns(returnsData);
      setChatSessions(sessionsData.slice(0, 3)); // Show only recent 3 sessions
    } catch (err) {
      setError('Failed to load dashboard data');
      console.error('Dashboard load error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateTaxReturn = async () => {
    try {
      const currentYear = new Date().getFullYear();
      const newReturn = await taxReturnService.createTaxReturn(currentYear);
      navigate(`/tax-return/${newReturn.id}`);
    } catch (err) {
      setError('Failed to create tax return');
      console.error('Create tax return error:', err);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'draft': return 'default';
      case 'computing': return 'info';
      case 'review': return 'warning';
      case 'approved': return 'success';
      case 'filed': return 'primary';
      default: return 'default';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'approved': return <CheckCircle />;
      case 'review': return <Warning />;
      default: return <Info />;
    }
  };

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      <Typography variant="h4" component="h1" gutterBottom sx={{ fontWeight: 'bold' }}>
        Welcome back, {user?.email?.split('@')[0]}!
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
        Manage your tax returns and get help with your non-resident tax filing.
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      <Grid container spacing={3}>
        {/* Quick Actions */}
        <Grid item xs={12} md={4}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Quick Actions
              </Typography>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                <Button
                  variant="contained"
                  startIcon={<Add />}
                  onClick={handleCreateTaxReturn}
                  fullWidth
                  disabled={loading}
                >
                  New Tax Return
                </Button>
                <Button
                  variant="outlined"
                  startIcon={<Chat />}
                  onClick={() => navigate('/chat')}
                  fullWidth
                >
                  Ask NRTaxAI
                </Button>
                <Button
                  variant="outlined"
                  startIcon={<Description />}
                  onClick={() => navigate('/documents')}
                  fullWidth
                >
                  Upload Documents
                </Button>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Tax Returns */}
        <Grid item xs={12} md={8}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6">
                  Your Tax Returns
                </Typography>
                <Button
                  size="small"
                  onClick={() => navigate('/tax-returns')}
                >
                  View All
                </Button>
              </Box>
              
              {taxReturns.length === 0 ? (
                <Paper sx={{ p: 3, textAlign: 'center', bgcolor: 'grey.50' }}>
                  <Description sx={{ fontSize: 48, color: 'grey.400', mb: 2 }} />
                  <Typography variant="body1" color="text.secondary" gutterBottom>
                    No tax returns yet
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Create your first tax return to get started
                  </Typography>
                </Paper>
              ) : (
                <List>
                  {taxReturns.slice(0, 5).map((taxReturn) => (
                    <ListItem
                      key={taxReturn.id}
                      sx={{
                        border: 1,
                        borderColor: 'grey.200',
                        borderRadius: 1,
                        mb: 1,
                        '&:hover': {
                          bgcolor: 'grey.50'
                        }
                      }}
                    >
                      <ListItemText
                        primary={`Tax Year ${taxReturn.tax_year}`}
                        secondary={
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 0.5 }}>
                            <Chip
                              label={taxReturn.status}
                              color={getStatusColor(taxReturn.status)}
                              size="small"
                              icon={getStatusIcon(taxReturn.status)}
                            />
                            <Typography variant="caption" color="text.secondary">
                              {new Date(taxReturn.created_at).toLocaleDateString()}
                            </Typography>
                          </Box>
                        }
                      />
                      <ListItemSecondaryAction>
                        <IconButton
                          edge="end"
                          onClick={() => navigate(`/tax-return/${taxReturn.id}`)}
                        >
                          <Assessment />
                        </IconButton>
                      </ListItemSecondaryAction>
                    </ListItem>
                  ))}
                </List>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Recent Chat Sessions */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6">
                  Recent Conversations
                </Typography>
                <Button
                  size="small"
                  onClick={() => navigate('/chat')}
                >
                  View All
                </Button>
              </Box>
              
              {chatSessions.length === 0 ? (
                <Paper sx={{ p: 3, textAlign: 'center', bgcolor: 'grey.50' }}>
                  <Chat sx={{ fontSize: 48, color: 'grey.400', mb: 2 }} />
                  <Typography variant="body1" color="text.secondary" gutterBottom>
                    No conversations yet
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Start chatting with our AI assistant to get help with your taxes
                  </Typography>
                </Paper>
              ) : (
                <List>
                  {chatSessions.map((session) => (
                    <ListItem
                      key={session.id}
                      sx={{
                        border: 1,
                        borderColor: 'grey.200',
                        borderRadius: 1,
                        mb: 1,
                        '&:hover': {
                          bgcolor: 'grey.50'
                        }
                      }}
                    >
                      <ListItemText
                        primary={`Session ${session.id.slice(0, 8)}...`}
                        secondary={
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 0.5 }}>
                            <Chip
                              label={session.status}
                              color={getStatusColor(session.status)}
                              size="small"
                            />
                            <Typography variant="caption" color="text.secondary">
                              {new Date(session.created_at).toLocaleDateString()}
                            </Typography>
                          </Box>
                        }
                      />
                      <ListItemSecondaryAction>
                        <IconButton
                          edge="end"
                          onClick={() => navigate('/chat')}
                        >
                          <Chat />
                        </IconButton>
                      </ListItemSecondaryAction>
                    </ListItem>
                  ))}
                </List>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Container>
  );
};

export default Dashboard;
