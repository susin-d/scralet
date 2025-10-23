// FIX: Implement the Customers component which was previously missing.
import React, { useState, useMemo } from 'react';
import Card from '../Card';
import Modal from '../Modal';
import { SearchIcon } from '../Icons';
import { MOCK_CUSTOMERS } from '../../constants';
import type { Customer } from '../../types';

const CustomerRow: React.FC<{ customer: Customer; onClick: () => void }> = ({ customer, onClick }) => (
  <tr className="border-b border-gray-700 hover:bg-gray-800 cursor-pointer" onClick={onClick}>
    <td className="py-3 px-4">
      <div className="flex items-center">
        <div className="w-10 h-10 rounded-full bg-accent flex items-center justify-center text-white font-bold">
          {customer.avatar}
        </div>
        <div className="ml-4">
          <div className="font-semibold text-text-primary">{customer.name}</div>
          <div className="text-sm text-text-secondary">{customer.email}</div>
        </div>
      </div>
    </td>
    <td className="py-3 px-4 text-center">
      <span
        className={`px-2 py-1 text-xs font-semibold rounded-full ${
          customer.loyaltyTier === 'Gold'
            ? 'bg-gold/20 text-gold'
            : customer.loyaltyTier === 'Silver'
            ? 'bg-gray-500/20 text-gray-300'
            : 'bg-yellow-700/20 text-yellow-500'
        }`}
      >
        {customer.loyaltyTier}
      </span>
    </td>
    <td className="py-3 px-4 text-text-secondary text-center">{customer.lastVisit}</td>
  </tr>
);

const CustomerDetailModal: React.FC<{ customer: Customer | null; onClose: () => void }> = ({ customer, onClose }) => {
    if (!customer) return null;

    return (
        <Modal isOpen={!!customer} onClose={onClose} title="Customer Details">
            <div className="flex flex-col items-center text-text-primary">
                <img src={customer.registrationPhoto} alt={customer.name} className="w-32 h-32 rounded-full object-cover mb-4" />
                <h2 className="text-2xl font-bold">{customer.name}</h2>
                <p className="text-text-secondary">{customer.email}</p>
                 <span
                    className={`mt-2 px-3 py-1 text-sm font-semibold rounded-full ${
                    customer.loyaltyTier === 'Gold'
                        ? 'bg-gold/20 text-gold'
                        : customer.loyaltyTier === 'Silver'
                        ? 'bg-gray-500/20 text-gray-300'
                        : 'bg-yellow-700/20 text-yellow-500'
                    }`}
                >
                    {customer.loyaltyTier} Tier
                </span>
                <div className="w-full text-left mt-6 space-y-2">
                    <p><strong>Last Visit:</strong> {customer.lastVisit}</p>
                    <p><strong>Customer ID:</strong> {customer.id}</p>
                </div>
            </div>
        </Modal>
    );
};

const SegmentCard: React.FC<{
  title: string;
  description: string;
  customers: Customer[];
  iconBgClass: string;
  icon: string;
}> = ({ title, description, customers, iconBgClass, icon }) => (
    <Card>
        <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${iconBgClass} text-2xl mb-4`}>
            {icon}
        </div>
        <p className="text-3xl font-bold text-text-primary">{customers.length}</p>
        <p className="font-semibold text-text-primary">{title}</p>
        <p className="text-sm text-text-secondary mt-1 h-10">{description}</p>
        <div className="flex -space-x-2 mt-4">
            {customers.slice(0, 5).map(c => (
                 <div key={c.id} title={c.name} className="w-8 h-8 rounded-full bg-accent flex items-center justify-center text-white font-bold text-xs ring-2 ring-gray-700">
                    {c.avatar}
                </div>
            ))}
            {customers.length > 5 && (
                 <div className="w-8 h-8 rounded-full bg-gray-600 flex items-center justify-center text-gray-300 font-bold text-xs ring-2 ring-gray-700">
                    +{customers.length - 5}
                </div>
            )}
        </div>
    </Card>
);

const Customers: React.FC = () => {
    const [selectedCustomer, setSelectedCustomer] = useState<Customer | null>(null);

    const segments = useMemo(() => {
        const isRecentVisit = (lastVisit: string, thresholdDays: number = 30): boolean => {
            const lastVisitDate = new Date(lastVisit);
            const today = new Date(); 
            const diffTime = Math.abs(today.getTime() - lastVisitDate.getTime());
            const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
            return diffDays <= thresholdDays;
        };
        
        const champions: Customer[] = [];
        const loyalCustomers: Customer[] = [];
        const potentialLoyalists: Customer[] = [];
        const atRisk: Customer[] = [];

        MOCK_CUSTOMERS.forEach(customer => {
            const isRecent = isRecentVisit(customer.lastVisit);
            if (customer.loyaltyTier === 'Gold' && isRecent) {
                champions.push(customer);
            } else if ((customer.loyaltyTier === 'Gold' && !isRecent) || customer.loyaltyTier === 'Silver') {
                loyalCustomers.push(customer);
            } else if (customer.loyaltyTier === 'Bronze' && isRecent) {
                potentialLoyalists.push(customer);
            } else if (customer.loyaltyTier === 'Bronze' && !isRecent) {
                atRisk.push(customer);
            }
        });

        return { champions, loyalCustomers, potentialLoyalists, atRisk };
    }, []);

    return (
        <div className="space-y-6">
            <h1 className="text-3xl font-bold text-text-primary">Customers</h1>
            
            <div>
                <h2 className="text-2xl font-semibold mb-4 text-text-primary">Customer Segments</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                    <SegmentCard 
                        title="Champions"
                        description="Your most valuable and active customers. Recently visited Gold tier members."
                        customers={segments.champions}
                        icon="🏆"
                        iconBgClass="bg-gold/20"
                    />
                     <SegmentCard 
                        title="Loyal Customers"
                        description="Consistent customers. Silver members or Gold members who haven't visited recently."
                        customers={segments.loyalCustomers}
                        icon="❤️"
                        iconBgClass="bg-accent/20"
                    />
                     <SegmentCard 
                        title="Potential Loyalists"
                        description="New or occasional customers who have visited recently. Nurture them to increase loyalty."
                        customers={segments.potentialLoyalists}
                        icon="🌱"
                        iconBgClass="bg-success/20"
                    />
                     <SegmentCard 
                        title="At Risk"
                        description="Inactive customers who haven't visited in a while. Re-engage them before they churn."
                        customers={segments.atRisk}
                        icon="⚠️"
                        iconBgClass="bg-error/20"
                    />
                </div>
            </div>

            <Card className="!p-0">
                <div className="p-4 flex justify-between items-center border-b border-gray-600">
                    <div className="relative">
                        <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                        <input
                            type="text"
                            placeholder="Search customers..."
                            className="pl-10 pr-4 py-2 w-72 rounded-lg bg-gray-800 border border-gray-600 focus:bg-gray-900 focus:border-accent focus:outline-none transition text-white"
                        />
                    </div>
                    <button className="px-4 py-2 bg-accent text-white rounded-lg font-semibold hover:opacity-90 transition-transform duration-200 ease-in-out hover:scale-105 active:scale-95">
                        Add Customer
                    </button>
                </div>
                <div className="overflow-x-auto">
                    <table className="w-full text-sm text-left">
                    <thead className="bg-gray-800 text-xs text-text-secondary uppercase tracking-wider">
                        <tr>
                        <th className="py-3 px-4 font-semibold">Customer</th>
                        <th className="py-3 px-4 font-semibold text-center">Loyalty Tier</th>
                        <th className="py-3 px-4 font-semibold text-center">Last Visit</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-700">
                        {MOCK_CUSTOMERS.map((customer) => (
                        <CustomerRow key={customer.id} customer={customer} onClick={() => setSelectedCustomer(customer)} />
                        ))}
                    </tbody>
                    </table>
                </div>
            </Card>

            <CustomerDetailModal customer={selectedCustomer} onClose={() => setSelectedCustomer(null)} />
        </div>
    );
};

export default Customers;