import React from 'react';
import { StoreIcon, DashboardIcon, CameraIcon, UsersIcon, SalesIcon, UserIcon, SettingsIcon, BellIcon } from './Icons';
import type { UserRole } from '../types';

interface SidebarProps {
  sidebarOpen: boolean;
  activePage: string;
  setActivePage: (page: string) => void;
  userRole: UserRole;
}

const NavItem: React.FC<{
  icon: React.ElementType;
  label: string;
  isActive: boolean;
  onClick: () => void;
}> = ({ icon: Icon, label, isActive, onClick }) => (
  <li>
    <a
      href="#"
      onClick={(e) => {
        e.preventDefault();
        onClick();
      }}
      className={`flex items-center p-3 rounded-lg transition-colors ${
        isActive
          ? 'bg-accent text-white font-semibold'
          : 'text-text-secondary hover:bg-gray-700 hover:text-white'
      }`}
    >
      <Icon className="w-6 h-6 mr-3" />
      <span>{label}</span>
    </a>
  </li>
);

const ADMIN_NAV = [
    { id: 'cameraView', label: 'Cameras', icon: CameraIcon },
    { id: 'customers', label: 'Customers', icon: UsersIcon },
    { id: 'dashboard', label: 'Analytics', icon: DashboardIcon },
    { id: 'alerts', label: 'Alerts', icon: BellIcon },
    { id: 'settings', label: 'Settings', icon: SettingsIcon },
];

const SALES_NAV = [
    { id: 'salesDashboard', label: 'Sales Dashboard', icon: SalesIcon },
    { id: 'customers', label: 'Customers', icon: UsersIcon },
];

const CUSTOMER_NAV = [
    { id: 'customerDashboard', label: 'My Dashboard', icon: UserIcon },
];


const Sidebar: React.FC<SidebarProps> = ({ sidebarOpen, activePage, setActivePage, userRole }) => {
  const navItems = {
      admin: ADMIN_NAV,
      sales: SALES_NAV,
      customer: CUSTOMER_NAV,
  }[userRole];

  return (
    <aside
      className={`fixed inset-y-0 left-0 bg-gray-900 z-30 w-64 p-4 transform transition-transform duration-300 md:relative md:translate-x-0 ${
        sidebarOpen ? 'translate-x-0' : '-translate-x-full'
      }`}
    >
      <div className="flex items-center mb-8 px-2">
        <svg className="w-8 h-8 text-white" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 14.08V7.92c0-.41.47-.65.8-.4l4.67 3.08c.33.22.33.64 0 .86l-4.67 3.08c-.33.25-.8.01-.8-.4z"/></svg>
        <span className="ml-3 text-2xl font-bold text-text-primary tracking-wider">PROJECT SCARLET</span>
      </div>

      <nav>
        <ul className="space-y-2">
          {navItems.map((item) => (
            <NavItem
              key={item.id}
              icon={item.icon}
              label={item.label}
              isActive={activePage === item.id}
              onClick={() => setActivePage(item.id)}
            />
          ))}
        </ul>
      </nav>
    </aside>
  );
};

// FIX: Add a default export for the Sidebar component to resolve the import error in App.tsx.
export default Sidebar;