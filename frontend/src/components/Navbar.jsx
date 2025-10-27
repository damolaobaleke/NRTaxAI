import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  AppBar,
  Toolbar,
  Typography,
  Button,
  IconButton,
  Menu,
  MenuItem,
  Box,
  Avatar,
  useTheme,
  useMediaQuery
} from '@mui/material';
import {
  AccountCircle,
  Menu as MenuIcon,
  Chat,
  Description,
  Dashboard,
  MenuBook
} from '@mui/icons-material';
import { useAuth } from '../contexts/AuthContext';

const Navbar = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout, isAuthenticated } = useAuth();
  const [anchorEl, setAnchorEl] = useState(null);
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));

  const handleMenu = (event) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const handleLogout = () => {
    logout();
    navigate('/');
    handleClose();
  };

  const handleNavigation = (path) => {
    navigate(path);
    handleClose();
  };

  const isActive = (path) => location.pathname === path;

  return (
    <AppBar position="static" elevation={1}>
      <Toolbar>
        <Typography
          variant="h6"
          component="div"
          sx={{ 
            flexGrow: 0, 
            mr: 4, 
            cursor: 'pointer',
            fontWeight: 'bold'
          }}
          onClick={() => navigate('/')}
        >
          NRTaxAI
        </Typography>

        {/* Forms Guide - accessible to all */}
        <Box sx={{ flexGrow: 1, display: 'flex', gap: 1 }}>
          {isAuthenticated && (
            <>
              <Button
                color="inherit"
                startIcon={<Dashboard />}
                onClick={() => navigate('/dashboard')}
                sx={{
                  backgroundColor: isActive('/dashboard') ? 'rgba(255,255,255,0.1)' : 'transparent'
                }}
              >
                Dashboard
              </Button>
              <Button
                color="inherit"
                startIcon={<Chat />}
                onClick={() => navigate('/chat')}
                sx={{
                  backgroundColor: isActive('/chat') ? 'rgba(255,255,255,0.1)' : 'transparent'
                }}
              >
                Chat
              </Button>
              <Button
                color="inherit"
                startIcon={<Description />}
                onClick={() => navigate('/tax-returns')}
                sx={{
                  backgroundColor: isActive('/tax-returns') ? 'rgba(255,255,255,0.1)' : 'transparent'
                }}
              >
                Tax Returns
              </Button>
            </>
          )}
          
          <Button
            color="inherit"
            startIcon={<MenuBook />}
            onClick={() => navigate('/forms-guide')}
            sx={{
              backgroundColor: isActive('/forms-guide') ? 'rgba(255,255,255,0.1)' : 'transparent'
            }}
          >
            Forms Guide
          </Button>
        </Box>

        <Box sx={{ flexGrow: 0 }} />

        {isAuthenticated ? (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Typography variant="body2" sx={{ display: { xs: 'none', sm: 'block' } }}>
              {user?.email}
            </Typography>
            <IconButton
              size="large"
              aria-label="account of current user"
              aria-controls="menu-appbar"
              aria-haspopup="true"
              onClick={handleMenu}
              color="inherit"
            >
              <Avatar sx={{ width: 32, height: 32, bgcolor: 'secondary.main' }}>
                {user?.email?.charAt(0).toUpperCase()}
              </Avatar>
            </IconButton>
            <Menu
              id="menu-appbar"
              anchorEl={anchorEl}
              anchorOrigin={{
                vertical: 'top',
                horizontal: 'right',
              }}
              keepMounted
              transformOrigin={{
                vertical: 'top',
                horizontal: 'right',
              }}
              open={Boolean(anchorEl)}
              onClose={handleClose}
            >
              <MenuItem onClick={() => handleNavigation('/profile')}>
                <AccountCircle sx={{ mr: 1 }} />
                Profile
              </MenuItem>
              <MenuItem onClick={handleLogout}>
                Logout
              </MenuItem>
            </Menu>
          </Box>
        ) : (
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Button
              color="inherit"
              onClick={() => navigate('/login')}
              sx={{
                backgroundColor: isActive('/login') ? 'rgba(255,255,255,0.1)' : 'transparent'
              }}
            >
              Login
            </Button>
            <Button
              color="inherit"
              variant="outlined"
              onClick={() => navigate('/register')}
              sx={{
                borderColor: 'white',
                color: 'white',
                '&:hover': {
                  borderColor: 'white',
                  backgroundColor: 'rgba(255,255,255,0.1)'
                }
              }}
            >
              Register
            </Button>
          </Box>
        )}
      </Toolbar>
    </AppBar>
  );
};

export default Navbar;
