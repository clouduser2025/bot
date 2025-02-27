import React, { useState } from 'react';
import {
  Container,
  Typography,
  TextField,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Box,
  CircularProgress,
  Alert,
} from '@mui/material';
import { Search, Download, Description, PlayArrow } from '@mui/icons-material';
import axios from 'axios';
import './App.css';

// Update to the EC2 public IP
const API_BASE_URL = 'http://13.126.32.105:8000';

function App() {
  const [city, setCity] = useState('');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState([]);
  const [error, setError] = useState('');
  const [foundPdf, setFoundPdf] = useState(null);
  const [downloadedPdfPath, setDownloadedPdfPath] = useState(null);
  const [excelFile, setExcelFile] = useState(null);

  const callApi = async (endpoint, method = 'GET', data = null) => {
    setLoading(true);
    setError('');
    try {
      const response = await axios({
        url: `${API_BASE_URL}${endpoint}`,
        method,
        data,
        headers: { 'Content-Type': 'application/json' },
      });
      const result = { endpoint, response: response.data, timestamp: new Date().toLocaleString() };
      setResults((prev) => [...prev, result]);

      if (endpoint === '/find-pdf/') {
        setFoundPdf(response.data.filename || null);
      } else if (endpoint === '/download-pdf/') {
        setDownloadedPdfPath(response.data.file_path || null);
      } else if (endpoint === '/extract-text/') {
        setExcelFile(response.data.excel_file || null);
      }
      return response.data;
    } catch (err) {
      setError(err.response?.data?.detail || 'An error occurred');
      return null;
    } finally {
      setLoading(false);
    }
  };

  const checkHealth = () => callApi('/');
  const findPdf = () => callApi('/find-pdf/', 'POST', { city });
  const downloadPdf = () => callApi('/download-pdf/', 'POST', { city });
  const extractText = async () => {
    const data = await callApi('/extract-text/', 'POST', {});
    if (data && data.excel_file) {
      const filename = data.excel_file.split('/').pop();
      const downloadUrl = `${API_BASE_URL}/download/${encodeURIComponent(filename)}`;
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
  };

  return (
    <Container
      maxWidth="lg"
      sx={{
        py: 6,
        px: 4,
        bgcolor: '#ffffff',
        borderRadius: 2,
        boxShadow: '0 4px 12px rgba(0, 0, 0, 0.1)',
        minHeight: '100vh',
      }}
    >
      <Typography
        variant="h2"
        gutterBottom
        align="center"
        sx={{
          color: '#1976d2',
          fontWeight: 700,
          textTransform: 'uppercase',
          letterSpacing: 2,
          mt: 4,
          mb: 6,
          textShadow: '1px 1px 2px rgba(0, 0, 0, 0.1)',
        }}
      >
        Newspaper Extractor
      </Typography>

      <Box
        sx={{
          p: 4,
          borderRadius: 2,
          boxShadow: '0 2px 8px rgba(0, 0, 0, 0.05)',
          bgcolor: '#fafafa',
          mb: 6,
        }}
      >
        <Typography
          variant="h4"
          gutterBottom
          sx={{ color: '#1976d2', fontWeight: 600, mb: 3 }}
        >
          Control Panel
        </Typography>
        <Box
          sx={{
            display: 'flex',
            gap: 2,
            flexWrap: 'wrap',
            alignItems: 'center',
            mb: 3,
          }}
        >
          <Button
            variant="contained"
            color="primary"
            onClick={checkHealth}
            disabled={loading}
            startIcon={<PlayArrow />}
            sx={{ borderRadius: 8, textTransform: 'none', py: 1, px: 3 }}
          >
            Check Health
          </Button>
          <TextField
            label="City Name"
            value={city}
            onChange={(e) => setCity(e.target.value)}
            variant="outlined"
            size="medium"
            sx={{ minWidth: 300, '& .MuiOutlinedInput-root': { borderRadius: 8 } }}
            InputProps={{
              endAdornment: loading && <CircularProgress size={20} color="inherit" />,
            }}
          />
          <Button
            variant="contained"
            color="secondary"
            onClick={findPdf}
            disabled={loading || !city}
            startIcon={<Search />}
            sx={{ borderRadius: 8, textTransform: 'none', py: 1, px: 3 }}
          >
            Find PDF
          </Button>
          {foundPdf && (
            <Button
              variant="contained"
              color="info"
              onClick={downloadPdf}
              disabled={loading}
              startIcon={<Download />}
              sx={{ borderRadius: 8, textTransform: 'none', py: 1, px: 3 }}
            >
              Download PDF
            </Button>
          )}
          {downloadedPdfPath && (
            <Button
              variant="contained"
              color="success"
              onClick={extractText}
              disabled={loading}
              startIcon={<Description />}
              sx={{ borderRadius: 8, textTransform: 'none', py: 1, px: 3 }}
            >
              Extract to Excel
            </Button>
          )}
          <Button
            variant="contained"
            color="warning"
            onClick={async () => {
              const downloadData = await downloadPdf();
              if (downloadData) await extractText();
            }}
            disabled={loading || !city}
            startIcon={<PlayArrow />}
            sx={{ borderRadius: 8, textTransform: 'none', py: 1, px: 3 }}
          >
            Download & Extract
          </Button>
        </Box>
        <Box sx={{ mt: 2 }}>
          {foundPdf && (
            <Typography variant="body1" sx={{ color: '#2e7d32', fontWeight: 500 }}>
              Found PDF: <span style={{ color: '#424242' }}>{foundPdf}</span>
            </Typography>
          )}
          {downloadedPdfPath && (
            <Typography variant="body1" sx={{ color: '#0288d1', fontWeight: 500, mt: 1 }}>
              Downloaded: <span style={{ color: '#424242' }}>{downloadedPdfPath.split('/').pop()}</span>
            </Typography>
          )}
          {excelFile && (
            <Typography variant="body1" sx={{ color: '#d32f2f', fontWeight: 500, mt: 1 }}>
              Extracted: <span style={{ color: '#424242' }}>{excelFile.split('/').pop()}</span>
            </Typography>
          )}
        </Box>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 4, borderRadius: 8, fontSize: '1rem' }}>
          {error}
        </Alert>
      )}

      <TableContainer
        component={Paper}
        sx={{
          boxShadow: '0 2px 8px rgba(0, 0, 0, 0.05)',
          borderRadius: 2,
          bgcolor: '#ffffff',
          mb: 4,
        }}
      >
        <Table>
          <TableHead>
            <TableRow sx={{ bgcolor: '#1976d2' }}>
              <TableCell sx={{ color: 'white', fontWeight: 'bold', fontSize: '1.1rem' }}>Endpoint</TableCell>
              <TableCell sx={{ color: 'white', fontWeight: 'bold', fontSize: '1.1rem' }}>Response</TableCell>
              <TableCell sx={{ color: 'white', fontWeight: 'bold', fontSize: '1.1rem' }}>Timestamp</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {results.map((result, index) => (
              <TableRow
                key={index}
                sx={{
                  '&:nth-of-type(odd)': { bgcolor: '#f5faff' },
                  transition: 'all 0.3s',
                  '&:hover': { bgcolor: '#e3f2fd' },
                }}
              >
                <TableCell sx={{ fontSize: '1rem' }}>{result.endpoint}</TableCell>
                <TableCell sx={{ fontSize: '0.95rem' }}>
                  <pre
                    style={{
                      margin: 0,
                      whiteSpace: 'pre-wrap',
                      wordWrap: 'break-word',
                      background: '#f9f9f9',
                      padding: 12,
                      borderRadius: 4,
                    }}
                  >
                    {JSON.stringify(result.response, null, 2)}
                  </pre>
                </TableCell>
                <TableCell sx={{ fontSize: '0.95rem', color: '#666' }}>{result.timestamp}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Container>
  );
}

export default App;