import React, { useState } from 'react';
import {
  Container,
  Typography,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  Box,
  TextField,
  InputAdornment,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Alert,
  AlertTitle,
} from '@mui/material';
import {
  Search as SearchIcon,
  ExpandMore as ExpandMoreIcon,
  Description as DescriptionIcon,
} from '@mui/icons-material';

const TaxFormsGuide = () => {
  const [searchTerm, setSearchTerm] = useState('');

  const taxForms = [
    {
      formCode: 'W-2',
      name: 'Wage and Tax Statement',
      category: 'Employment',
      description: 'Reports your annual wages and the amount of taxes withheld from your paycheck. Issued by your employer.',
      whoNeedsIt: 'All employees (H1B, L-1, O-1, etc.)',
      keyFields: ['Wages (Box 1)', 'Federal tax withheld (Box 2)', 'Social Security wages (Box 3)', 'Medicare wages (Box 5)'],
      deadline: 'January 31',
      importance: 'Critical',
    },
    {
      formCode: '1099-NEC',
      name: 'Nonemployee Compensation',
      category: 'Self-Employment',
      description: 'Reports income received as an independent contractor or freelancer.',
      whoNeedsIt: 'Contractors, freelancers, consultants',
      keyFields: ['Nonemployee compensation (Box 1)', 'Federal tax withheld (Box 4)'],
      deadline: 'January 31',
      importance: 'Critical',
    },
    {
      formCode: '1099-INT',
      name: 'Interest Income',
      category: 'Investment',
      description: 'Reports interest income from banks, savings accounts, and bonds.',
      whoNeedsIt: 'Anyone earning $10+ in interest',
      keyFields: ['Interest income (Box 1)', 'Federal tax withheld (Box 4)'],
      deadline: 'January 31',
      importance: 'High',
    },
    {
      formCode: '1099-DIV',
      name: 'Dividends and Distributions',
      category: 'Investment',
      description: 'Reports dividend income from stocks, mutual funds, and capital gain distributions.',
      whoNeedsIt: 'Stock/fund investors',
      keyFields: ['Total ordinary dividends (Box 1a)', 'Qualified dividends (Box 1b)', 'Capital gain distributions (Box 2a)', 'Foreign tax paid (Box 6)'],
      deadline: 'January 31',
      importance: 'High',
    },
    {
      formCode: '1099-B',
      name: 'Broker Transactions',
      category: 'Investment',
      description: 'Reports proceeds from selling stocks, bonds, or other securities through a broker.',
      whoNeedsIt: 'Investors who sold securities',
      keyFields: ['Proceeds (Box 1d)', 'Cost basis (Box 1e)', 'Gain/loss (Box 1g)', 'Federal tax withheld (Box 4)'],
      deadline: 'February 15',
      importance: 'High',
    },
    {
      formCode: '1099-G',
      name: 'Government Payments',
      category: 'Government',
      description: 'Reports unemployment compensation, state tax refunds, and other government payments.',
      whoNeedsIt: 'Recipients of unemployment or state tax refunds',
      keyFields: ['Unemployment compensation (Box 1)', 'State tax refund (Box 2)', 'Federal tax withheld (Box 4)', 'State tax withheld (Box 11)'],
      deadline: 'January 31',
      importance: 'Medium',
    },
    {
      formCode: '1099-MISC',
      name: 'Miscellaneous Income',
      category: 'Other Income',
      description: 'Reports various types of income including rent, royalties, prizes, and awards.',
      whoNeedsIt: 'Recipients of rental income, royalties, or other miscellaneous income',
      keyFields: ['Rents (Box 1)', 'Royalties (Box 2)', 'Other income (Box 3)', 'Federal tax withheld (Box 4)'],
      deadline: 'January 31',
      importance: 'Medium',
    },
    {
      formCode: '1099-R',
      name: 'Retirement Distributions',
      category: 'Retirement',
      description: 'Reports distributions from pensions, annuities, retirement plans, IRAs, or insurance contracts.',
      whoNeedsIt: 'Recipients of retirement distributions',
      keyFields: ['Gross distribution (Box 1)', 'Taxable amount (Box 2a)', 'Federal tax withheld (Box 4)', 'Distribution code (Box 7)'],
      deadline: 'January 31',
      importance: 'High',
    },
    {
      formCode: '1098-T',
      name: 'Tuition Statement',
      category: 'Education',
      description: 'Reports qualified tuition and related expenses. Used to claim education credits like American Opportunity Credit.',
      whoNeedsIt: 'F-1 students and anyone paying tuition',
      keyFields: ['Payments received (Box 1)', 'Qualified tuition (Box 2)', 'Scholarships/grants (Box 5)', 'Half-time student (Box 8)'],
      deadline: 'January 31',
      importance: 'Critical for F-1 students',
    },
    {
      formCode: '1042-S',
      name: 'Foreign Person\'s U.S. Source Income',
      category: 'Non-Resident Specific',
      description: 'Reports U.S. source income paid to foreign persons, including scholarships, fellowships, and grants for non-residents.',
      whoNeedsIt: 'Non-resident aliens with U.S. scholarships, fellowships, or grants',
      keyFields: ['Income code (Box 1)', 'Gross income (Box 2)', 'Exemption codes (Box 3a, 4a)', 'Tax rate (Box 5)', 'Federal tax withheld (Box 7a)', 'Country code'],
      deadline: 'March 15',
      importance: 'Critical for NR aliens',
    },
  ];

  const filteredForms = taxForms.filter(
    (form) =>
      form.formCode.toLowerCase().includes(searchTerm.toLowerCase()) ||
      form.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      form.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
      form.category.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const getImportanceColor = (importance) => {
    if (importance.includes('Critical')) return 'error';
    if (importance === 'High') return 'warning';
    return 'info';
  };

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h3" gutterBottom sx={{ fontWeight: 'bold', color: 'primary.main' }}>
          <DescriptionIcon sx={{ fontSize: 40, mr: 2, verticalAlign: 'middle' }} />
          Tax Forms Knowledge Base
        </Typography>
        <Typography variant="h6" color="text.secondary" gutterBottom>
          Complete guide to tax forms for non-resident aliens
        </Typography>
      </Box>

      <Alert severity="info" sx={{ mb: 4 }}>
        <AlertTitle>For Non-Resident Aliens</AlertTitle>
        These are the common tax forms you may receive while on F-1, H1B, O-1, or other non-immigrant visas.
        Upload these documents to NRTaxAI for automatic data extraction and tax calculation.
      </Alert>

      <TextField
        fullWidth
        variant="outlined"
        placeholder="Search forms by code, name, or category..."
        value={searchTerm}
        onChange={(e) => setSearchTerm(e.target.value)}
        sx={{ mb: 4 }}
        InputProps={{
          startAdornment: (
            <InputAdornment position="start">
              <SearchIcon />
            </InputAdornment>
          ),
        }}
      />

      <TableContainer component={Paper} elevation={3} sx={{ mb: 4 }}>
        <Table>
          <TableHead sx={{ bgcolor: 'primary.main' }}>
            <TableRow>
              <TableCell sx={{ color: 'white', fontWeight: 'bold' }}>Form Code</TableCell>
              <TableCell sx={{ color: 'white', fontWeight: 'bold' }}>Name</TableCell>
              <TableCell sx={{ color: 'white', fontWeight: 'bold' }}>Category</TableCell>
              <TableCell sx={{ color: 'white', fontWeight: 'bold' }}>Who Needs It</TableCell>
              <TableCell sx={{ color: 'white', fontWeight: 'bold' }}>Deadline</TableCell>
              <TableCell sx={{ color: 'white', fontWeight: 'bold' }}>Importance</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {filteredForms.map((form) => (
              <TableRow key={form.formCode} hover sx={{ '&:hover': { bgcolor: 'action.hover' } }}>
                <TableCell>
                  <Typography variant="body1" fontWeight="bold" color="primary">
                    {form.formCode}
                  </Typography>
                </TableCell>
                <TableCell>{form.name}</TableCell>
                <TableCell>
                  <Chip label={form.category} size="small" variant="outlined" />
                </TableCell>
                <TableCell>{form.whoNeedsIt}</TableCell>
                <TableCell>{form.deadline}</TableCell>
                <TableCell>
                  <Chip
                    label={form.importance}
                    color={getImportanceColor(form.importance)}
                    size="small"
                  />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <Typography variant="h5" gutterBottom sx={{ fontWeight: 'bold', mb: 3 }}>
        Detailed Information
      </Typography>

      {filteredForms.map((form) => (
        <Accordion key={form.formCode} sx={{ mb: 2 }}>
          <AccordionSummary
            expandIcon={<ExpandMoreIcon />}
            sx={{ bgcolor: 'grey.50' }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', width: '100%' }}>
              <Typography variant="h6" sx={{ fontWeight: 'bold', color: 'primary.main', mr: 2 }}>
                {form.formCode}
              </Typography>
              <Typography variant="body1" sx={{ flexGrow: 1 }}>
                {form.name}
              </Typography>
              <Chip
                label={form.importance}
                color={getImportanceColor(form.importance)}
                size="small"
              />
            </Box>
          </AccordionSummary>
          <AccordionDetails>
            <Box sx={{ p: 2 }}>
              <Typography variant="body1" paragraph>
                <strong>Description:</strong> {form.description}
              </Typography>
              
              <Typography variant="body1" paragraph>
                <strong>Who Needs It:</strong> {form.whoNeedsIt}
              </Typography>
              
              <Typography variant="body1" paragraph>
                <strong>Deadline:</strong> {form.deadline}
              </Typography>
              
              <Typography variant="body1" gutterBottom>
                <strong>Key Fields Extracted by NRTaxAI:</strong>
              </Typography>
              <Box component="ul" sx={{ mt: 1, pl: 3 }}>
                {form.keyFields.map((field, idx) => (
                  <Typography component="li" key={idx} variant="body2" sx={{ mb: 0.5 }}>
                    {field}
                  </Typography>
                ))}
              </Box>
            </Box>
          </AccordionDetails>
        </Accordion>
      ))}

      <Paper sx={{ p: 3, mt: 4, bgcolor: 'info.light' }}>
        <Typography variant="h6" gutterBottom sx={{ fontWeight: 'bold' }}>
          💡 Need Help?
        </Typography>
        <Typography variant="body1">
          Upload any of these forms to NRTaxAI and our AI will automatically extract the data,
          validate it, and use it to prepare your 1040-NR tax return. No manual data entry required!
        </Typography>
      </Paper>
    </Container>
  );
};

export default TaxFormsGuide;

