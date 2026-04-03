import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Home from './pages/Home';
import History from './pages/History';
import Form from './pages/Form';
import { ToastProvider } from './contexts/ToastContext';
import ToastContainer from './components/ToastContainer';

function App() {
  return (
    <ToastProvider>
      <Router>
        <Layout>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/history" element={<History />} />
            <Route path="/form" element={<Form />} />
          </Routes>
        </Layout>
      </Router>
      <ToastContainer />
    </ToastProvider>
  );
}

export default App;
