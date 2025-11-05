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
import ReactMarkdown from 'react-markdown';
import { chatService, documentService, taxReturnService } from '../services/apiService';
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

    // Store message content before clearing input
    const messageToSend = inputMessage;
    
    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);
    setIsTyping(true);

    try {
      const response = await chatService.sendMessage(currentSession.id, messageToSend);
      
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
        content: response.message || response.content || 'I received your message.',
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

  // Helper function to detect document type from filename
  const detectDocumentType = (filename) => {
    const lowerName = filename.toLowerCase();
    
    // Check for common document patterns
    if (lowerName.includes('w2') || lowerName.includes('w-2')) return 'W2';
    if (lowerName.includes('1099-int') || lowerName.includes('1099int')) return '1099INT';
    if (lowerName.includes('1099-nec') || lowerName.includes('1099nec')) return '1099NEC';
    if (lowerName.includes('1099-div') || lowerName.includes('1099div')) return '1099DIV';
    if (lowerName.includes('1099-misc') || lowerName.includes('1099misc')) return '1099MISC';
    if (lowerName.includes('1099-b') || lowerName.includes('1099b')) return '1099B';
    if (lowerName.includes('1098-t') || lowerName.includes('1098t')) return '1098T';
    if (lowerName.includes('1042-s') || lowerName.includes('1042s')) return '1042S';
    
    // Default to W2 if cannot detect
    return 'W2';
  };

  // Helper function to store assistant message in database via chat service
  const storeAssistantMessageInDB = async (content, toolCalls = null) => {
    if (!currentSession) return;

    try {
      // Store the assistant message using the chat service
      await chatService.storeMessage(
        currentSession.id,
        'assistant',
        content,
        toolCalls
      );
    } catch (error) {
      console.error('Failed to store message in DB:', error);
      // Don't throw - we still want to show the message in UI even if DB storage fails
    }
  };

  // Helper function to store user message in database
  const storeUserMessageInDB = async (content) => {
    if (!currentSession) return;

    try {
      await chatService.storeMessage(
        currentSession.id,
        'user',
        content
      );
    } catch (error) {
      console.error('Failed to store user message in DB:', error);
    }
  };

  // Helper function to poll extraction status until completion
  const pollExtractionStatus = async (documentId, maxAttempts = 30, interval = 2000) => {
    let attempts = 0;
    
    while (attempts < maxAttempts) {
      try {
        const result = await documentService.getExtractionResult(documentId);
        
        // Check if extraction is complete
        if (result.status === 'extracted' || result.status === 'validation_failed') {
          return result;
        }
        
        // If still processing, wait and try again
        if (result.status === 'processing') {
          await new Promise(resolve => setTimeout(resolve, interval));
          attempts++;
          continue;
        }
        
        // If failed, return the result
        if (result.status === 'failed') {
          return result;
        }
        
        // Wait before next attempt
        await new Promise(resolve => setTimeout(resolve, interval));
        attempts++;
      } catch (error) {
        console.error('Error polling extraction status:', error);
        throw error;
      }
    }
    
    throw new Error('Extraction polling timeout - maximum attempts reached');
  };

  // Helper function to get common tax forms that might be needed
  const getCommonTaxForms = () => {
    return ['W2', '1099INT', '1099NEC', '1099DIV', '1099MISC', '1098T', '1042S'];
  };

  // Helper function to check for missing tax forms
  const checkMissingTaxForms = async (returnId, uploadedDocType) => {
    if (!returnId) return [];
    
    try {
      // Get all documents for this return
      const documents = await documentService.getDocuments(returnId);
      
      // Get uploaded document types
      const uploadedTypes = documents.map(doc => doc.doc_type);
      
      // Common tax forms that might be needed
      const commonForms = getCommonTaxForms();
      
      // Filter out the form that was just uploaded
      const missingForms = commonForms.filter(form => 
        !uploadedTypes.includes(form) && form !== uploadedDocType
      );
      
      return missingForms;
    } catch (error) {
      console.error('Error checking missing tax forms:', error);
      return [];
    }
  };

  // Helper function to ask about missing tax forms
  const askAboutMissingForms = async (missingForms, uploadedDocType) => {
    if (missingForms.length === 0) {
      return false; // No missing forms, proceed with computation
    }
    
    // Create a message asking about missing forms
    const formNames = missingForms.map(form => {
      const formMap = {
        'W2': 'W-2',
        '1099INT': '1099-INT',
        '1099NEC': '1099-NEC',
        '1099DIV': '1099-DIV',
        '1099MISC': '1099-MISC',
        '1099B': '1099-B',
        '1098T': '1098-T',
        '1042S': '1042-S'
      };
      return formMap[form] || form;
    });
    
    const messageContent = `📋 I've extracted information from your ${uploadedDocType} document. 

Before I can compute your tax return, I need to know if you have any other tax forms. Common forms include:
${formNames.map(form => `- ${form}`).join('\n')}

Do you have any of these forms? If yes, please upload them. If no, I'll proceed with what we have.`;
    
    const assistantMessage = {
      id: Date.now() + 1000,
      role: 'assistant',
      content: messageContent,
      timestamp: new Date(),
      status: 'received'
    };
    
    setMessages(prev => [...prev, assistantMessage]);
    
    // Store message in DB (if endpoint exists)
    await storeAssistantMessageInDB(messageContent);
    
    // Return true to indicate we're waiting for user response
    return true;
  };

  const handleFileUpload = () => {
    fileInputRef.current?.click();
  };

  const processFileUpload = async (file, session) => {
    // Create a message showing file upload
    const fileMessage = {
      id: Date.now(),
      role: 'user',
      content: `📎 Uploading file: ${file.name}`,
      timestamp: new Date(),
      status: 'sending'
    };
    
    setMessages(prev => [...prev, fileMessage]);
    
    // Store user message in DB
    await storeUserMessageInDB(fileMessage.content);

    let uploadResult = null;
    let confirmResult = null;
    try {
      setIsLoading(true);
      setError(null);
      
      // Step 1: Detect document type from filename
      const docType = detectDocumentType(file.name);
      
      // Step 2: Request upload URL from backend (creates document record)
      const uploadData = await documentService.requestUploadUrl(docType, session?.return_id || null);

      // Step 3: Upload file directly to S3 no presigned POST URL (avoids CORS issues)
      uploadResult = await documentService.uploadFile(uploadData.document_id, file);
      console.log("uploadResult", uploadResult);

      // Step 4: If upload is successful, confirm upload and initiate Antivirus or malware scan
      if(uploadResult && uploadResult.status === 'uploaded') {
        // Update message to show success
        const uploadSuccessContent = `📎 Uploaded file: ${file.name} (${docType}) successfully`;
        setMessages(prev => 
          prev.map(msg => 
            msg.id === fileMessage.id 
              ? { 
                  ...msg, 
                  status: 'sent',
                  content: uploadSuccessContent
                }
              : msg
          )
        );
        // Store updated user message in DB
        await storeUserMessageInDB(uploadSuccessContent);
        
        // "Now scanning for malware..." message as string (not JSX)
        const scanningMessage = {
          id: Date.now() + 2,
          role: 'assistant',
          content: '🦠 Scanning file for malware/antivirus...',
          timestamp: new Date(),
          status: 'scanning'
        };

        setMessages(prev => [...prev, scanningMessage]);
        await storeAssistantMessageInDB(scanningMessage.content);

        // Step 5: Confirm upload and initiate Antivirus or malware scan
        confirmResult = await documentService.confirmUpload(uploadData.document_id);
        console.log("confirmResult", confirmResult);
        
        // Remove scanning message and add final result
        setMessages(prev => 
          prev.filter(msg => msg.id !== scanningMessage.id)
        );
        
        if(confirmResult && confirmResult.status === 'clean') {
          // Automatically start extraction
          const extractionStartMessage = {
            id: Date.now() + 3,
            role: 'assistant',
            content: `✅ The document has been scanned and is clean. Starting information extraction...`,
            timestamp: new Date(),
            status: 'processing'
          };
          
          setMessages(prev => [...prev, extractionStartMessage]);
          await storeAssistantMessageInDB(extractionStartMessage.content);
          
          try {
            // Start extraction
            const extractionStart = await documentService.startExtraction(uploadData.document_id);
            console.log("Extraction started:", extractionStart);
            
            // Update message to show extraction in progress
            const extractionProgressContent = '🔄 Extracting information from document... This may take a few moments.';
            setMessages(prev => 
              prev.map(msg => 
                msg.id === extractionStartMessage.id 
                  ? { 
                      ...msg, 
                      content: extractionProgressContent,
                      status: 'processing'
                    }
                  : msg
              )
            );
            // Store the updated message
            await storeAssistantMessageInDB(extractionProgressContent);
            
            // Poll for extraction status
            const extractionResult = await pollExtractionStatus(uploadData.document_id);
            console.log("Extraction result:", extractionResult);
            
            // Remove processing message and add completion message
            setMessages(prev => 
              prev.filter(msg => msg.id !== extractionStartMessage.id)
            );
            
            if (extractionResult.status === 'extracted') {
              // Extraction successful
              const successMessage = {
                id: Date.now() + 4,
                role: 'assistant',
                content: `✅ Successfully extracted information from your ${docType} document!`,
                timestamp: new Date(),
                status: 'received'
              };
              
              setMessages(prev => [...prev, successMessage]);
              await storeAssistantMessageInDB(successMessage.content);
              
              // Get document details to retrieve return_id
              let returnId = session?.return_id;
              try {
                const documentDetails = await documentService.getDocument(uploadData.document_id);
                returnId = returnId || documentDetails.return_id;
              } catch (error) {
                console.error('Failed to get document details:', error);
              }
              
              if (returnId) {
                const missingForms = await checkMissingTaxForms(returnId, docType);
                const waitingForForms = await askAboutMissingForms(missingForms, docType);
                
                // If no missing forms or user has indicated they don't have more, proceed with computation
                if (!waitingForForms) {
                  // Wait a bit for user to see the message, then proceed with computation
                  setTimeout(async () => {
                    try {
                      const computeMessage = {
                        id: Date.now() + 5,
                        role: 'assistant',
                        content: '💼 Starting tax computation...',
                        timestamp: new Date(),
                        status: 'processing'
                      };
                      
                      setMessages(prev => [...prev, computeMessage]);
                      await storeAssistantMessageInDB(computeMessage.content);
                      
                      const computationResult = await taxReturnService.computeTax(returnId);
                      console.log("Tax computation result:", computationResult);
                      
                      // Update message with computation result
                      setMessages(prev => 
                        prev.map(msg => 
                          msg.id === computeMessage.id 
                            ? { 
                                ...msg, 
                                content: `✅ Tax computation completed! Your tax return has been processed.`,
                                status: 'received'
                              }
                            : msg
                        )
                      );
                      
                      await storeAssistantMessageInDB(`✅ Tax computation completed! Your tax return has been processed.`);
                    } catch (error) {
                      console.error('Tax computation error:', error);
                      const errorMessage = {
                        id: Date.now() + 6,
                        role: 'assistant',
                        content: `❌ Failed to compute tax return: ${error.response?.data?.detail || error.message}`,
                        timestamp: new Date(),
                        status: 'received'
                      };
                      
                      setMessages(prev => [...prev, errorMessage]);
                      await storeAssistantMessageInDB(errorMessage.content);
                    }
                  }, 2000); // Wait 2 seconds before starting computation
                }
              } else {
                // No return_id, so we can't compute tax yet
                const noReturnMessage = {
                  id: Date.now() + 5,
                  role: 'assistant',
                  content: `📄 Extraction complete! To compute your tax return, please create or select a tax return first.`,
                  timestamp: new Date(),
                  status: 'received'
                };
                
                setMessages(prev => [...prev, noReturnMessage]);
                await storeAssistantMessageInDB(noReturnMessage.content);
              }
            } else if (extractionResult.status === 'validation_failed') {
              // Extraction completed but validation failed
              const validationMessage = {
                id: Date.now() + 4,
                role: 'assistant',
                content: `⚠️ Information extracted, but some fields failed validation. Please review the extracted data.`,
                timestamp: new Date(),
                status: 'received'
              };
              
              setMessages(prev => [...prev, validationMessage]);
              await storeAssistantMessageInDB(validationMessage.content);
            } else {
              // Extraction failed
              const errorMessage = {
                id: Date.now() + 4,
                role: 'assistant',
                content: `❌ Failed to extract information from document: ${extractionResult.error || 'Unknown error'}`,
                timestamp: new Date(),
                status: 'received'
              };
              
              setMessages(prev => [...prev, errorMessage]);
              await storeAssistantMessageInDB(errorMessage.content);
            }
          } catch (error) {
            console.error('Extraction error:', error);
            const errorMessage = {
              id: Date.now() + 4,
              role: 'assistant',
              content: `❌ Failed to start extraction: ${error.response?.data?.detail || error.message}`,
              timestamp: new Date(),
              status: 'received'
            };
            
            setMessages(prev => [...prev, errorMessage]);
            await storeAssistantMessageInDB(errorMessage.content);
          }
        } else if(confirmResult && confirmResult.status === 'quarantined') {
          const assistantMessage = {
            id: Date.now() + 3,
            role: 'assistant',
            content: `❌ The document has been scanned and quarantined due to security threats. Please contact support if you believe this is an error.`,
            timestamp: new Date(),
            status: 'received'
          };
          setMessages(prev => [...prev, assistantMessage]);
          await storeAssistantMessageInDB(assistantMessage.content);
        }
      } else {
        console.log("uploadResult", uploadResult);
        setError('Upload failed or returned unexpected status');
      }
      
    } catch (error) {
      console.log(error);
      console.error('File upload error:', error);
      const errorMessage = error?.response?.data?.detail || error?.message || 'Unknown error occurred';
      setError(`${errorMessage}`);
      
      // Update message to show failure with safe property access
      const errorContent = uploadResult?.status === 'uploaded' 
        ? `Uploaded successfully, but failed to confirm upload: ${confirmResult?.status || 'unknown error'}` 
        : `Failed to upload: ${errorMessage}`;
      
      setMessages(prev => 
        prev.map(msg => 
          msg.id === fileMessage.id 
            ? { 
                ...msg, 
                status: 'failed', 
                content: errorContent
              }
            : msg
        )
      );
      
      // Store error message in DB
      await storeUserMessageInDB(errorContent);
    } finally {
      setIsLoading(false);
    }
  };

  const handleFileChange = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    // Validate file type
    const allowedTypes = ['application/pdf', 'image/png', 'image/jpeg', 'image/jpg'];
    if (!allowedTypes.includes(file.type)) {
      setError('Please select a PDF, PNG, or JPEG file');
      e.target.value = '';
      return;
    }

    // Validate file size (10MB limit)
    const maxSize = 10 * 1024 * 1024; // 10MB
    if (file.size > maxSize) {
      setError('File size must be less than 10MB');
      e.target.value = '';
      return;
    }

    // Create a new session if none exists
    if (!currentSession) {
      try {
        const newSession = await chatService.createSession(null);
        setSessions(prev => [newSession, ...prev]);
        setCurrentSession(newSession);
        setMessages([]);
        // Now process the file upload with the new session
        await processFileUpload(file, newSession);
      } catch (error) {
        console.error('Failed to create session for file upload:', error);
        setError('Failed to create session. Please try again.');
      } finally {
        e.target.value = '';
      }
      return;
    }
    
    // Process file upload with existing session
    await processFileUpload(file, currentSession);
    e.target.value = '';
  };

  const formatTimestamp = (timestamp) => {
    // console.log("timestamp", timestamp)
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
          color: message.role === 'user' ? 'white' : 'black',
          borderRadius: 2,
          p: 2,
          position: 'relative'
        }}
      >
        <Box sx={{ mb: 1 }}>
          <ReactMarkdown
            components={{
              // Custom styling for markdown elements
              p: ({ children }) => <Typography variant="body1" sx={{ mb: 1 }}>{children}</Typography>,
              h1: ({ children }) => <Typography variant="h4" sx={{ mb: 2, mt: 2 }}>{children}</Typography>,
              h2: ({ children }) => <Typography variant="h5" sx={{ mb: 2, mt: 2 }}>{children}</Typography>,
              h3: ({ children }) => <Typography variant="h6" sx={{ mb: 1, mt: 2 }}>{children}</Typography>,
              h4: ({ children }) => <Typography variant="subtitle1" sx={{ mb: 1, mt: 1, fontWeight: 'bold' }}>{children}</Typography>,
              h5: ({ children }) => <Typography variant="subtitle2" sx={{ mb: 1, mt: 1, fontWeight: 'bold' }}>{children}</Typography>,
              h6: ({ children }) => <Typography variant="body1" sx={{ mb: 1, mt: 1, fontWeight: 'bold' }}>{children}</Typography>,
              ul: ({ children }) => <Box component="ul" sx={{ pl: 2, mb: 1 }}>{children}</Box>,
              ol: ({ children }) => <Box component="ol" sx={{ pl: 2, mb: 2 }}>{children}</Box>,
              li: ({ children }) => <Box component="li" sx={{ mb: 1 }}>{children}</Box>,
              strong: ({ children }) => <Typography component="span" sx={{ fontWeight: 'bold' }}>{children}</Typography>,
              em: ({ children }) => <Typography component="span" sx={{ fontStyle: 'italic' }}>{children}</Typography>,
              code: ({ children }) => (
                <Box
                  component="code"
                  sx={{
                    backgroundColor: 'grey.100',
                    px: 1,
                    py: 0.5,
                    borderRadius: 1,
                    fontFamily: 'monospace',
                    fontSize: '0.875rem'
                  }}
                >
                  {children}
                </Box>
              ),
              pre: ({ children }) => (
                <Box
                  component="pre"
                  sx={{
                    backgroundColor: 'grey.100',
                    p: 2,
                    borderRadius: 1,
                    overflow: 'auto',
                    fontFamily: 'monospace',
                    fontSize: '0.875rem',
                    mb: 1
                  }}
                >
                  {children}
                </Box>
              ),
              blockquote: ({ children }) => (
                <Box
                  sx={{
                    borderLeft: 4,
                    borderColor: 'primary.main',
                    pl: 2,
                    ml: 2,
                    mb: 1,
                    fontStyle: 'italic'
                  }}
                >
                  {children}
                </Box>
              )
            }}
          >
            {message.content}
          </ReactMarkdown>
          {/* {console.log("message role:", message.role)}
          {console.log("message content:", message.content)} */}
        </Box>
        
        {renderToolCalls(message.toolCalls)}
        
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mt: 1 }}>
          <Typography variant="caption" color={message.role === 'user' ? 'white' : 'text.secondary'}>
            {formatTimestamp(message.timestamp || message.created_at || new Date())}
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
                  secondary={session.created_at ? new Date(session.created_at).toLocaleDateString() : 'No date'}
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