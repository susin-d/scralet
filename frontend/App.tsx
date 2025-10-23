// FIX: Implement the main App component to resolve module resolution errors.
// This component was previously missing, causing build failures. It now serves as the main layout,
// managing application state for navigation and rendering the appropriate page components.
import React, { useState } from 'react';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import Dashboard from './components/pages/Dashboard';
import CameraView from './components/pages/CameraView';
import Customers from './components/pages/Customers';
import SalesDashboard from './components/pages/SalesDashboard';
import CustomerDashboard from './components/pages/CustomerDashboard';
import LoginPage from './components/pages/LoginPage';
import type { UserRole } from './types';

const App: React.FC = () => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [activePage, setActivePage] = useState('cameraView');
  const [userRole, setUserRole] = useState<UserRole>('admin');

  const handleSetUserRole = (role: UserRole) => {
    setUserRole(role);
    // Reset to a default page for that role
    if (role === 'admin') setActivePage('cameraView');
    if (role === 'sales') setActivePage('salesDashboard');
    if (role === 'customer') setActivePage('customerDashboard');
  };

  const handleLoginSuccess = () => {
    setIsAuthenticated(true);
  };


  const renderContent = () => {
    if (userRole === 'admin') {
        switch (activePage) {
            case 'dashboard': return <Dashboard />;
            case 'cameraView': return <CameraView />;
            case 'customers': return <Customers />;
            default: return <CameraView />;
        }
    }
    if (userRole === 'sales') {
        switch (activePage) {
            case 'salesDashboard': return <SalesDashboard />;
            case 'customers': return <Customers />;
            default: return <SalesDashboard />;
        }
    }
    if (userRole === 'customer') {
        switch (activePage) {
            case 'customerDashboard': return <CustomerDashboard />;
            default: return <CustomerDashboard />;
        }
    }
    return <div>Access Denied</div>;
  };

  if (!isAuthenticated) {
    return <LoginPage onLoginSuccess={handleLoginSuccess} />;
  }

  return (
    <div className="flex h-screen bg-gray-800 text-text-primary overflow-hidden">
      <Sidebar
        sidebarOpen={sidebarOpen}
        activePage={activePage}
        setActivePage={setActivePage}
        userRole={userRole}
      />
      <div className="flex-1 flex flex-col">
        <Header 
          sidebarOpen={sidebarOpen} 
          setSidebarOpen={setSidebarOpen} 
          userRole={userRole}
          setUserRole={handleSetUserRole}
        />
        <main className="flex-1 overflow-y-auto p-6 lg:p-8 bg-gray-800">
          {renderContent()}
        </main>
      </div>
    </div>
  );
};

export default App;