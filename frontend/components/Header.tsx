import React, { useState } from 'react';
import { MenuIcon, BellIcon, ChevronDownIcon } from './Icons';
import type { UserRole } from '../types';
import { MOCK_LOGGED_IN_CUSTOMER, MOCK_SALES_REP } from '../constants';

interface HeaderProps {
  sidebarOpen: boolean;
  setSidebarOpen: (open: boolean) => void;
  userRole: UserRole;
  setUserRole: (role: UserRole) => void;
}

const ADMIN_USER = { name: 'Admin', title: 'Administrator', avatar: 'A' };

const UserProfile: React.FC<{ user: { name: string, title: string, avatar: string } }> = ({ user }) => (
    <div className="flex items-center space-x-3 cursor-pointer">
        <div className="hidden md:block text-right">
            <div className="font-semibold text-sm text-text-primary">{user.name}</div>
        </div>
    </div>
);

const RoleSwitcher: React.FC<{ userRole: UserRole, setUserRole: (role: UserRole) => void }> = ({ userRole, setUserRole }) => {
    const [isOpen, setIsOpen] = useState(false);

    const handleRoleChange = (role: UserRole) => {
        setUserRole(role);
        setIsOpen(false);
    }

    return (
        <div className="relative">
            <button onClick={() => setIsOpen(!isOpen)} className="flex items-center p-2 rounded-md hover:bg-gray-700">
                <span className="font-semibold text-sm mr-2 capitalize text-text-primary">{userRole}</span>
                <ChevronDownIcon className={`w-4 h-4 text-text-secondary transition-transform ${isOpen ? 'rotate-180' : ''}`} />
            </button>
            {isOpen && (
                <div className="absolute right-0 mt-2 w-48 bg-gray-700 rounded-md shadow-lg py-1 z-20 border border-gray-600">
                    <a href="#" onClick={(e) => { e.preventDefault(); handleRoleChange('admin')}} className="block px-4 py-2 text-sm text-text-secondary hover:bg-gray-600 hover:text-white">Administrator</a>
                    <a href="#" onClick={(e) => { e.preventDefault(); handleRoleChange('sales')}} className="block px-4 py-2 text-sm text-text-secondary hover:bg-gray-600 hover:text-white">Sales Rep</a>
                    <a href="#" onClick={(e) => { e.preventDefault(); handleRoleChange('customer')}} className="block px-4 py-2 text-sm text-text-secondary hover:bg-gray-600 hover:text-white">Customer</a>
                </div>
            )}
        </div>
    );
};

const Header: React.FC<HeaderProps> = ({ sidebarOpen, setSidebarOpen, userRole, setUserRole }) => {
  
  const currentUser = {
      admin: ADMIN_USER,
      sales: MOCK_SALES_REP,
      customer: { name: MOCK_LOGGED_IN_CUSTOMER.name, title: 'Customer', avatar: MOCK_LOGGED_IN_CUSTOMER.avatar },
  }[userRole];

  return (
    <header className="flex-shrink-0 bg-gray-900 h-16 flex items-center justify-between px-6 z-10 border-b border-gray-700">
      <div className="flex items-center">
        <button onClick={() => setSidebarOpen(!sidebarOpen)} className="text-gray-400 hover:text-white focus:outline-none md:hidden">
          <MenuIcon className="w-6 h-6" />
        </button>
      </div>

      <div className="flex items-center space-x-4">
        <RoleSwitcher userRole={userRole} setUserRole={setUserRole} />
        
        <div className="relative">
            <button className="p-2 rounded-full hover:bg-gray-700">
                <BellIcon className="w-6 h-6 text-text-secondary" />
            </button>
            <span className="absolute top-1 right-1 block h-2.5 w-2.5 rounded-full bg-error ring-2 ring-gray-900"></span>
        </div>

        <UserProfile user={currentUser} />
      </div>
    </header>
  );
};

export default Header;