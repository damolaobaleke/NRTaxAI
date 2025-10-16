import React, { useState, useEffect, useRef } from 'react';
import {
  Container,
  Typography,
  Paper,
  Box,
  TextField,
  IconButton,
  List,
  ListItem,
  ListItemText,
  Avatar,
  Chip,
  CircularProgress,
  Alert,
  Divider,
  Card,
  CardContent,
  Button,
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
  Send,
  SmartToy,
  Person,
  Refresh,
  Add,
  History,
  Delete,
  AttachFile,
  Code,
  Calculate,
  Description
} from '@mui/icons-material';
import { chatService } from '../services/authService';
import { useAuth } from '../contexts/AuthContext';

const ChatPage = () => {
  const { user } = useAuth();
  const [sessions, setSessions] = useState([]);
  const [currentSession, setCurrentSession] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [error, setError] = useState(null);
  const [newSessionDialog, setNewSessionDialog] = useState(false);
  const [selectedTaxReturn, setSelectedTaxReturn] = useState('');
  const [taxReturns, setTaxReturns] = useState([]);
  
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const fileInputRef = useRef(null);

  // Scroll to bottom when new messages arrive
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Load user sessions and tax returns on component mount
  useEffect(() => {
    loadSessions();
    loadTaxReturns();
  }, []);

  const loadSessions = async () => {
    try {
      const userSessions = await chatService.getUserSessions();
      setSessions(userSessions);
      if (userSessions.length > 0 && !currentSession) {
        setCurrentSession(userSessions[0]);
        loadChatHistory(userSessions[0].id);
      }
    } catch (error) {
      console.error('Failed to load sessions:', error);
      setError('Failed to load chat sessions');
    }
  };

  const loadTaxReturns = async () => {
    try {
      // This would integrate with your tax return service
      // For now, we'll use a placeholder
      setTaxReturns([]);
    } catch (error) {
      console.error('Failed to load tax returns:', error);
    }
  };

  const loadChatHistory = async (sessionId) => {
    try {
      const history = await chatService.getChatHistory(sessionId);
      setMessages(history.messages || []);
    } catch (error) {
      console.error('Failed to load chat history:', error);
      setError('Failed to load chat history');
    }
  };

  const createNewSession = async () => {
    try {
      setIsLoading(true);
      const newSession = await chatService.createSession(selectedTaxReturn || null);
      setSessions(prev => [newSession, ...prev]);
      setCurrentSession(newSession);
      setMessages([]);
      setNewSessionDialog(false);
      setSelectedTaxReturn('');
    } catch (error) {
      console.error('Failed to create session:', error);
      setError('Failed to create new chat session');
    } finally {
      setIsLoading(false);
    }
  };

  const createNewSessionSeamless = async () => {
    try {
      const newSession = await chatService.createSession(null); // No tax return needed for seamless creation
      setSessions(prev => [newSession, ...prev]);
      setCurrentSession(newSession);
      setMessages([]);
      
      // Now that we have a session, send the message directly
      const userMessage = {
        id: Date.now(),
        role: 'user',
        content: inputMessage,
        timestamp: new Date(),
        status: 'sending'
      };

      setMessages(prev => [...prev, userMessage]);
      const messageToSend = inputMessage;
      setInputMessage('');
      setIsLoading(true);
      setIsTyping(true);

      try {
        const response = await chatService.sendMessage(newSession.id, messageToSend);
        
        // Update user message status
        setMessages(prev => 
          prev.map(msg => 
            msg.id === userMessage.id 
              ? { ...msg, status: 'sent' }
              : msg
          )
        );

        // Add AI response
        const aiMessage = {
          id: Date.now() + 1,
          role: 'assistant',
          content: response.content || 'I received your message.',
          timestamp: new Date(),
          status: 'sent',
          toolCalls: response.tool_calls || []
        };
        setMessages(prev => [...prev, aiMessage]);
      } catch (error) {
        console.error('Error sending message:', error);
        setMessages(prev => 
          prev.map(msg => 
            msg.id === userMessage.id 
              ? { ...msg, status: 'failed' }
              : msg
          )
        );
        setError('Failed to send message');
      } finally {
        setIsLoading(false);
        setIsTyping(false);
      }
    } catch (error) {
      console.error('Failed to create session:', error);
      setError('Failed to create new chat session');
    }
  };

  const sendMessage = async () => {
    if (!inputMessage.trim()) return;
    
    // Create a new session if none exists (seamless, no dialog)
    if (!currentSession) {
      await createNewSessionSeamless();
      return; // createNewSessionSeamless handles the entire flow
    }

    const userMessage = {
      id: Date.now(),
      role: 'user',
      content: inputMessage,
      timestamp: new Date(),
      status: 'sending'
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);
    setIsTyping(true);

    try {
      const response = await chatService.sendMessage(currentSession.id, inputMessage);
      
      // Update user message status
      setMessages(prev => 
        prev.map(msg => 
          msg.id === userMessage.id 
            ? { ...msg, status: 'sent' }
            : msg
        )
      );

      // Add AI response
      const aiMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: response.message,
        timestamp: new Date(),
        toolCalls: response.tool_calls || [],
        status: 'received'
      };

      setMessages(prev => [...prev, aiMessage]);
    } catch (error) {
      console.error('Failed to send message:', error);
      setError('Failed to send message. Please try again.');
      
      // Update user message status to failed
      setMessages(prev => 
        prev.map(msg => 
          msg.id === userMessage.id 
            ? { ...msg, status: 'failed' }
            : msg
        )
      );
    } finally {
      setIsLoading(false);
      setIsTyping(false);
    }
  };

  const handleKeyPress = (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  };

  const handleFileUpload = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    // Create a new session if none exists
    if (!currentSession) {
      await createNewSession();
      // Wait a bit for session to be created, then try again
      setTimeout(() => handleFileChange(e), 1000);
      return;
    }

    try {
      setIsLoading(true);
      
      // Create a message showing file upload
      const fileMessage = {
        id: Date.now(),
        role: 'user',
        content: `📎 Uploaded file: ${file.name}`,
        timestamp: new Date(),
        status: 'sending'
      };
      
      setMessages(prev => [...prev, fileMessage]);
      
      // Here you would typically upload the file to your backend
      // For now, we'll just simulate success
      setTimeout(() => {
        setMessages(prev => 
          prev.map(msg => 
            msg.id === fileMessage.id 
              ? { ...msg, status: 'sent' }
              : msg
          )
        );
        setIsLoading(false);
      }, 1000);
      
    } catch (error) {
      console.error('File upload error:', error);
      setError('Failed to upload file');
      setIsLoading(false);
    }
    
    // Reset file input
    e.target.value = '';
  };

  const formatTimestamp = (timestamp) => {
    return new Date(timestamp).toLocaleTimeString([], { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  };

  const getMessageIcon = (role) => {
    return role === 'user' ? <Person /> : <SmartToy />;
  };

  const getMessageStatusIcon = (status) => {
    switch (status) {
      case 'sending':
        return <CircularProgress size={16} />;
      case 'sent':
        return <span style={{ color: 'green' }}>✓</span>;
      case 'failed':
        return <span style={{ color: 'red' }}>✗</span>;
      default:
        return null;
    }
  };

  const renderToolCalls = (toolCalls) => {
    if (!toolCalls || toolCalls.length === 0) return null;

    return (
      <Box sx={{ mt: 1 }}>
        {toolCalls.map((call, index) => (
          <Chip
            key={index}
            icon={call.type === 'calculation' ? <Calculate /> : <Description />}
            label={`${call.type}: ${call.description}`}
            size="small"
            variant="outlined"
            sx={{ mr: 1, mb: 1 }}
          />
        ))}
      </Box>
    );
  };

  const renderMessage = (message) => (
    <ListItem
      key={message.id}
      sx={{
        flexDirection: message.role === 'user' ? 'row-reverse' : 'row',
        alignItems: 'flex-start',
        mb: 2
      }}
    >
      <Avatar
        sx={{
          bgcolor: message.role === 'user' ? 'primary.main' : 'secondary.main',
          mx: 1
        }}
      >
        {getMessageIcon(message.role)}
      </Avatar>
      
      <Box
        sx={{
          maxWidth: '70%',
          bgcolor: message.role === 'user' ? 'primary.light' : 'grey.100',
          borderRadius: 2,
          p: 2,
          position: 'relative'
        }}
      >
        <Typography variant="body1" sx={{ mb: 1 }}>
          {message.content}
        </Typography>
        
        {renderToolCalls(message.toolCalls)}
        
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mt: 1 }}>
          <Typography variant="caption" color="text.secondary">
            {formatTimestamp(message.timestamp)}
          </Typography>
          {message.role === 'user' && getMessageStatusIcon(message.status)}
        </Box>
      </Box>
    </ListItem>
  );

  return (
    <Container maxWidth="lg" sx={{ mt: 2, mb: 4 }}>
      <Box sx={{ display: 'flex', height: '80vh' }}>
        {/* Sidebar */}
        <Paper sx={{ width: 300, mr: 2, p: 2, display: 'flex', flexDirection: 'column' }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="h6">Chats</Typography>
          </Box>
          
          {/* New Chat Button */}
          <Button
            variant="outlined"
            startIcon={<Add />}
            onClick={() => {
              setCurrentSession(null);
              setMessages([]);
              setInputMessage('');
            }}
            sx={{ mb: 2, justifyContent: 'flex-start' }}
            fullWidth
          >
            New Chat
          </Button>
          
          <List sx={{ flexGrow: 1, overflow: 'auto' }}>
            {sessions.map((session) => (
              <ListItem
                key={session.id}
                button
                selected={currentSession?.id === session.id}
                onClick={() => {
                  setCurrentSession(session);
                  loadChatHistory(session.id);
                }}
                sx={{
                  borderRadius: 1,
                  mb: 0.5,
                  '&.Mui-selected': {
                    backgroundColor: 'primary.main',
                    color: 'primary.contrastText',
                    '&:hover': {
                      backgroundColor: 'primary.dark',
                    }
                  }
                }}
              >
                <ListItemText
                  primary={`Chat ${session.id.slice(-8)}`}
                  secondary={new Date(session.created_at).toLocaleDateString()}
                  primaryTypographyProps={{ fontSize: '0.9rem' }}
                  secondaryTypographyProps={{ fontSize: '0.75rem' }}
                />
              </ListItem>
            ))}
          </List>
          
          <Divider sx={{ my: 2 }} />
          
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Button
              variant="outlined"
              startIcon={<Refresh />}
              onClick={loadSessions}
              size="small"
              fullWidth
            >
              Refresh
            </Button>
            <Button
              variant="outlined"
              startIcon={<History />}
              size="small"
              fullWidth
            >
              History
            </Button>
          </Box>
        </Paper>

        {/* Main Chat Area */}
        <Paper sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
          {/* Chat Header */}
          <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
            <Typography variant="h6">
              {currentSession ? `Chat Session ${currentSession.id.slice(-8)}` : 'AI Tax Filing Assistant'}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Ask me anything about your taxes, forms, or filing process
            </Typography>
          </Box>

          {/* Messages Area */}
          <Box sx={{ flexGrow: 1, overflow: 'auto', p: 1 }}>
            {error && (
              <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
                {error}
              </Alert>
            )}
            
            {messages.length === 0 ? (
              <Box sx={{ textAlign: 'center', py: 4 }}>
                <SmartToy sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
                <Typography variant="h6" color="text.secondary" gutterBottom>
                  {currentSession ? 'Start a conversation' : `Good to see you, ${user?.email?.split('@')[0]}!`}
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                  {currentSession 
                    ? 'Ask me anything about your taxes, forms, or filing process'
                    : 'Click "New Chat" to start a conversation or select an existing chat from the sidebar'
                  }
                </Typography>
                {!currentSession && (
                  <Button
                    variant="contained"
                    startIcon={<Add />}
                    onClick={() => {
                      setCurrentSession(null);
                      setMessages([]);
                      setInputMessage('');
                    }}
                    sx={{ mt: 2 }}
                  >
                    Start New Chat
                  </Button>
                )}
              </Box>
            ) : (
              <List>
                {messages.map(renderMessage)}
                {isTyping && (
                  <ListItem sx={{ justifyContent: 'flex-start' }}>
                    <Avatar sx={{ bgcolor: 'secondary.main', mx: 1 }}>
                      <SmartToy />
                    </Avatar>
                    <Box sx={{ bgcolor: 'grey.100', borderRadius: 2, p: 2 }}>
                      <CircularProgress size={16} sx={{ mr: 1 }} />
                      <Typography variant="body2" color="text.secondary">
                        NRTaxAI is thinking...
                      </Typography>
                    </Box>
                  </ListItem>
                )}
                <div ref={messagesEndRef} />
              </List>
            )}
          </Box>

          {/* Input Area */}
          <Box sx={{ p: 2, borderTop: 1, borderColor: 'divider' }}>
            <Box sx={{ display: 'flex', gap: 1 }}>
              <TextField
                ref={inputRef}
                fullWidth
                multiline
                maxRows={4}
                placeholder="Ask me about your taxes..."
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyDown={handleKeyPress}
                disabled={isLoading}
                variant="outlined"
                size="small"
              />
              <IconButton
                onClick={sendMessage}
                disabled={!inputMessage.trim() || isLoading}
                color="primary"
                sx={{ alignSelf: 'flex-end' }}
              >
                <Send />
              </IconButton>
            </Box>
            
            <Box sx={{ display: 'flex', gap: 1, mt: 1 }}>
              <IconButton 
                size="small" 
                onClick={handleFileUpload}
                disabled={isLoading}
                title="Attach file"
              >
                <AttachFile />
              </IconButton>
              <IconButton size="small" disabled title="Code block (coming soon)">
                <Code />
              </IconButton>
            </Box>
            
            {/* Hidden file input */}
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileChange}
              style={{ display: 'none' }}
              accept=".pdf,.doc,.docx,.jpg,.jpeg,.png,.txt"
            />
          </Box>
        </Paper>
      </Box>

      {/* New Session Dialog */}
      <Dialog open={newSessionDialog} onClose={() => setNewSessionDialog(false)}>
        <DialogTitle>Create New Chat Session</DialogTitle>
        <DialogContent>
          <FormControl fullWidth sx={{ mt: 2 }}>
            <InputLabel>Tax Return (Optional)</InputLabel>
            <Select
              value={selectedTaxReturn}
              onChange={(e) => setSelectedTaxReturn(e.target.value)}
              label="Tax Return (Optional)"
            >
              <MenuItem value="">No specific tax return</MenuItem>
              {taxReturns.map((taxReturn) => (
                <MenuItem key={taxReturn.id} value={taxReturn.id}>
                  {taxReturn.tax_year} - {taxReturn.status}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setNewSessionDialog(false)}>Cancel</Button>
          <Button onClick={createNewSession} variant="contained" disabled={isLoading}>
            {isLoading ? <CircularProgress size={20} /> : 'Create Session'}
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default ChatPage;