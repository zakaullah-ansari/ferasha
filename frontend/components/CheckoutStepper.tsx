import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Check, ChevronRight, ChevronLeft, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card } from '@/components/ui/card';
import { cn } from '@/lib/utils';

type Step = 'address' | 'shipping' | 'tax' | 'review';

interface CheckoutStepperProps {
  onComplete: (data: any) => void;
}

export const CheckoutStepper: React.FC<CheckoutStepperProps> = ({ onComplete }) => {
  const [currentStep, setCurrentStep] = useState<Step>('address');
  const [isLoading, setIsLoading] = useState(false);
  const [formData, setFormData] = useState({
    address: { street: '', city: '', state: '', pincode: '', country: 'India' },
    shippingCost: 0,
    taxQuote: null as any,
  });

  const steps: { id: Step; label: string }[] = [
    { id: 'address', label: 'Atelier Shipping' },
    { id: 'shipping', label: 'Delivery Method' },
    { id: 'tax', label: 'Imperial Duties' },
    { id: 'review', label: 'Final Review' },
  ];

  const nextStep = () => {
    const currentIndex = steps.findIndex((s) => s.id === currentStep);
    if (currentIndex < steps.length - 1) {
      setCurrentStep(steps[currentIndex + 1].id);
    }
  };

  const prevStep = () => {
    const currentIndex = steps.findIndex((s) => s.id === currentStep);
    if (currentIndex > 0) {
      setCurrentStep(steps[currentIndex - 1].id);
    }
  };

  const handleAddressSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    // Simulate backend call to /api/v1/checkout/validate-address/
    setTimeout(() => {
      setIsLoading(false);
      nextStep();
    }, 800);
  };

  return (
    <div className="max-w-2xl mx-auto w-full space-y-8 p-6">
      {/* Progress Header */}
      <div className="relative flex justify-between items-center px-4">
        {steps.map((step, idx) => (
          <React.Fragment key={step.id}>
            <div className="flex flex-col items-center gap-2 z-10">
              <div
                className={cn(
                  "w-8 h-8 rounded-full flex items-center justify-center transition-all duration-500",
                  currentStep === step.id
                    ? "bg-primary text-primary-foreground scale-110 shadow-lg"
                    : steps.find(s => s.id === currentStep) && steps.indexOf(steps.find(s => s.id === currentStep)!) > idx
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted text-muted-foreground"
                )}
              >
                {steps.find(s => s.id === currentStep) && steps.indexOf(steps.find(s => s.id === currentStep)!) > idx ? (
                  <Check className="w-4 h-4" />
                ) : (
                  <span className="text-xs font-medium">{idx + 1}</span>
                )}
              </div>
              <span className={cn(
                "text-[10px] uppercase tracking-widest font-medium transition-colors",
                currentStep === step.id ? "text-primary" : "text-muted-foreground"
              )}>
                {step.label}
              </span>
            </div>
            {idx < steps.length - 1 && (
              <div className="flex-1 h-[1px] mx-2 bg-border relative">
                <motion.div
                  className="absolute inset-0 bg-primary"
                  initial={{ width: '0%' }}
                  animate={{ width: currentStep === step.id ? '100%' : currentStep === 'address' ? '0%' : '100%' }}
                  transition={{ duration: 0.5, ease: 'easeOut' }}
                />
              </div>
            )}
          </React.Fragment>
        ))}
      </div>

      {/* Step Content */}
      <AnimatePresence mode="wait">
        <motion.div
          key={currentStep}
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -20 }}
          transition={{ duration: 0.3, ease: 'easeOut' }}
        >
          {currentStep === 'address' && (
            <Card className="glass-regular glass-highlight p-8 border-none shadow-xl">
              <div className="space-y-6">
                <div className="text-center space-y-2">
                  <h2 className="font-display text-display-sm text-ink-900">Shipping Details</h2>
                  <p className="text-sm text-muted-foreground italic">Where shall we deliver your couture piece?</p>
                </div>
                <form onSubmit={handleAddressSubmit} className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="md:col-span-2 space-y-2">
                    <Label className="text-xs uppercase tracking-tighter">Street Address</Label>
                    <Input
                      className="bg-transparent border-ink-200 focus:border-primary"
                      placeholder="Flat 402, Imperial Heights"
                      required
                      onChange={(e) => setFormData({...formData, address: {...formData.address, street: e.target.value}})}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label className="text-xs uppercase tracking-tighter">City</Label>
                    <Input
                      className="bg-transparent border-ink-200"
                      placeholder="Mumbai"
                      required
                      onChange={(e) => setFormData({...formData, address: {...formData.address, city: e.target.value}})}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label className="text-xs uppercase tracking-tighter">State</Label>
                    <Input
                      className="bg-transparent border-ink-200"
                      placeholder="Maharashtra"
                      required
                      onChange={(e) => setFormData({...formData, address: {...formData.address, state: e.target.value}})}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label className="text-xs uppercase tracking-tighter">Pincode</Label>
                    <Input
                      className="bg-transparent border-ink-200"
                      placeholder="400001"
                      required
                      onChange={(e) => setFormData({...formData, address: {...formData.address, pincode: e.target.value}})}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label className="text-xs uppercase tracking-tighter">Country</Label>
                    <Input
                      className="bg-transparent border-ink-200"
                      value={formData.address.country}
                      readOnly
                    />
                  </div>
                  <div className="md:col-span-2 pt-4">
                    <Button
                      type="submit"
                      className="w-full bg-primary text-primary-foreground hover:bg-primary/90 transition-all h-12"
                      disabled={isLoading}
                    >
                      {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Continue to Shipping"}
                      <ChevronRight className="ml-2 w-4 h-4" />
                    </Button>
                  </div>
                </form>
              </div>
            </Card>
          )}

          {currentStep === 'shipping' && (
            <Card className="glass-regular glass-highlight p-8 border-none shadow-xl">
              <div className="space-y-6">
                <div className="text-center space-y-2">
                  <h2 className="font-display text-display-sm text-ink-900">Delivery Selection</h2>
                  <p className="text-sm text-muted-foreground italic">Choose your preferred delivery speed</p>
                </div>
                <div className="space-y-3">
                  {[
                    { id: 'standard', name: 'Standard Delivery', price: '₹150', time: '5-7 Business Days' },
                    { id: 'express', name: 'Atelier Express', price: '₹500', time: '2-3 Business Days' },
                    { id: 'concierge', name: 'White Glove Concierge', price: '₹1,200', time: 'Next Day' },
                  ].map((option) => (
                    <div
                      key={option.id}
                      className={cn(
                        "p-4 rounded-lg border transition-all cursor-pointer flex justify-between items-center",
                        "hover:border-primary hover:bg-primary/5",
                        "border-ink-200"
                      )}
                      onClick={() => setFormData({...formData, shippingCost: 150})}
                    >
                      <div>
                        <p className="font-medium text-ink-900">{option.name}</p>
                        <p className="text-xs text-muted-foreground">{option.time}</p>
                      </div>
                      <p className="font-display text-ink-900">{option.price}</p>
                    </div>
                  ))}
                </div>
                <div className="flex gap-4 pt-4">
                  <Button variant="outline" onClick={prevStep} className="flex-1 h-12">Back</Button>
                  <Button onClick={nextStep} className="flex-1 bg-primary text-primary-foreground h-12">Continue</Button>
                </div>
              </div>
            </Card>
          )}

          {currentStep === 'tax' && (
            <Card className="glass-regular glass-highlight p-8 border-none shadow-xl">
              <div className="space-y-6 text-center">
                <h2 className="font-display text-display-sm text-ink-900">Imperial Duties</h2>
                <div className="bg-ink-50 p-6 rounded-lg border border-ink-100 space-y-3 text-left max-w-xs mx-auto">
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">CGST (Central)</span>
                    <span className="font-medium">₹250.00</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">SGST (State)</span>
                    <span className="font-medium">₹250.00</span>
                  </div>
                  <div className="border-t border-ink-200 my-2" />
                  <div className="flex justify-between font-medium">
                    <span>Total Tax</span>
                    <span>₹500.00</span>
                  </div>
                </div>
                <div className="flex gap-4 pt-4">
                  <Button variant="outline" onClick={prevStep} className="flex-1 h-12">Back</Button>
                  <Button onClick={nextStep} className="flex-1 bg-primary text-primary-foreground h-12">Continue</Button>
                </div>
              </div>
            </Card>
          )}

          {currentStep === 'review' && (
            <Card className="glass-regular glass-highlight p-8 border-none shadow-xl">
              <div className="space-y-6">
                <div className="text-center space-y-2">
                  <h2 className="font-display text-display-sm text-ink-900">Final Review</h2>
                  <p className="text-sm text-muted-foreground italic">Verify your order details before finalizing</p>
                </div>
                <div className="space-y-4 text-sm">
                  <div className="p-4 rounded-lg bg-ink-50 border border-ink-100">
                    <p className="text-xs uppercase tracking-widest text-muted-foreground mb-2">Shipping To</p>
                    <p className="text-ink-900 font-medium">{formData.address.street}</p>
                    <p className="text-ink-900">{formData.address.city}, {formData.address.state} - {formData.address.pincode}</p>
                  </div>
                  <div className="p-4 rounded-lg bg-ink-50 border border-ink-100 flex justify-between items-center">
                    <div>
                      <p className="text-xs uppercase tracking-widest text-muted-foreground">Shipping</p>
                      <p className="text-ink-900 font-medium">Standard Delivery</p>
                    </div>
                    <p className="font-medium">₹{formData.shippingCost}</p>
                  </div>
                  <div className="p-4 rounded-lg bg-ink-50 border border-ink-100 flex justify-between items-center">
                    <div>
                      <p className="text-xs uppercase tracking-widest text-muted-foreground">Tax Estimate</p>
                      <p className="text-ink-900 font-medium">GST (Standard)</p>
                    </div>
                    <p className="font-medium">₹500.00</p>
                  </div>
                </div>
                <div className="flex gap-4 pt-4">
                  <Button variant="outline" onClick={prevStep} className="flex-1 h-12">Back</Button>
                  <Button
                    onClick={() => onComplete(formData)}
                    className="flex-1 bg-primary text-primary-foreground h-12 font-medium"
                  >
                    Place Order
                    <ChevronRight className="ml-2 w-4 h-4" />
                  </Button>
                </div>
              </div>
            </Card>
          )}
        </motion.div>
      </AnimatePresence>
    </div>
  );
};
