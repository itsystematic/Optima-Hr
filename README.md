# Optima HR for Saudi Arabia

**Optima HR** is a revolutionary application for **Frappe HRMS** that fully implements Saudi Arabia's labor laws. This app introduces advanced features to streamline HR operations, automate attendance management, and ensure compliance with labor regulations in the Kingdom of Saudi Arabia. Designed with comprehensive Arabic language support, **Optima HR** is tailored to meet the unique needs of businesses operating in the Saudi Arabia market.

---

## 🚀 Main Features

**Optima HR** offers a wide range of features to transform your HR management:

### **Attendance Management**
- Automatic calculation of attendance, including:
  - **Late arrivals** and **early departures**, with penalties applied based on Saudi labor law.
- Support for **single-shift** and **two-shift** work schedules.
- Correct Arabic formatting for attendance records.

### **Leave Management**
- Comprehensive leave types based on Saudi labor laws, with the relevant legal text displayed for each type of leave.
- Accurate calculation and payment of **end-of-service benefits** (EOSB) for all cases under Saudi labor law.
- Calculation and payment of **annual leave** for non-Saudi employees.

### **Penalties Actions**
- Automated penalties for violations, with a progressive system:
  - First, second, third, and fourth occurrences handled according to Saudi labor law.

### **Payroll Management**
- Generate **Excel-based payroll files** ready for submission to the bank.
- Create all required **salary components** pre-configured for immediate use.
- Add individual or bulk **HR Salary Effects** for employees, like incentives or deductions.

### **HR Letters and Forms**
- Generate all essential HR letters directly from the system.
- Dedicated **resignation request document** for employees.
- **Return-from-leave** and **first-time work resumption** documents to streamline employee onboarding and return processes.

### **Travel and Allowances**
- Manage **local and international travel tickets**, categorized by type.
- Support for all nationalities of expatriate employees in Saudi Arabia.

### **Time-Off Requests**
- Manage **employee time-off requests** with:
  - Workflow approvals.
  - Custom rules, such as a maximum of **6 hours per month** and **2 hours per request**.
- Separate management for **business errands** to avoid conflicts with personal time-off.

### **Employee Loans and Advances**
- Restructured **employee loan management**:
  - Short-term advances deducted from the next salary.
  - Long-term advances deducted through predefined installments.

### **Comprehensive Reports**
- **Payroll Report**: Bank-ready payroll disbursement report.
- **Employee Advances Report**: Track all loans and advances.
- **Employee Time-Off Report**: Detailed view of time-off requests.
- **Employee Penalties Report**: Overview of all disciplinary actions.

### **Arabic Language Support**
- Human-made, human-reviewed Arabic translations for all buttons, messages, and terms, ensuring alignment with Saudi workforce terminology.

### **System Customization**
- **HR Settings Document**: Configure the HR application based on your company’s internal policies.

---

## 💡 Why Choose Optima HR?

1. **Full Compliance**: Implements all aspects of Saudi labor law.
2. **Ease of Use**: Streamlined workflows for HR processes.
3. **Comprehensive Features**: Covers all critical HR and payroll needs.
4. **Arabic Localization**: Full Arabic translation with workplace-appropriate terminology.
5. **Customizable**: Allows companies to configure HR policies to fit their needs.

---

## 📦 Installation

Follow these steps to install **Optima HR** on your Frappe HRMS setup:

1. Clone the repository:
   ```bash
   bench get-app https://github.com/itsystematic/Optima-Hr.git
   ```
2. Install requirements:
   ```bash
   bench setup requirements
   ```
3. Build the app:
   ```bash
   bench build --app optima_hr
   ```
4. Restart the bench:
   ```bash
   bench restart
   ```
5. Install the app on your site:
   ```bash
   bench --site [your.site.name] install-app optima_hr
   ```
6. Run migrations:
   ```bash
   bench --site [your.site.name] migrate
   ```

---

## 🛠️ How to Use

- Configure the application through the **HR Settings Document** to align with your company’s policies.
- Access features for attendance, payroll, leave management, and disciplinary actions from the HR module.
- Generate reports and export payroll-ready files in Excel format.

### Supported Frappe Versions
- Frappe HRMS Version 15

---

## 📞 Support

We provide dedicated support to ensure a seamless experience with **Optima HR**:

- For premium support or feature requests, contact us at:  
  **support@itsystematic.com**

### **Issue Reporting**
- Found a bug or have a feature request? Create an issue after reviewing existing ones:  
  [GitHub Issues](https://github.com/itsystematic/Optima-Hr/issues)

---

## 🤝 Contributing

We welcome contributions from the community! Please follow our contribution guidelines outlined in the **Contributing Guide**.

### Guidelines
- Submit issues through **GitHub Issues**.
- Follow best practices for pull requests.
- Ensure thorough testing before submitting.

---

## 📜 License

**Optima HR** is licensed under the **GPL-3.0 License**. See the full license in the [LICENSE](https://github.com/itsystematic/Optima-Hr/blob/version-15/LICENSE) file.

---

## 📂 More Apps by IT Systematic

Explore other powerful apps developed by IT Systematic:

- **[Optima ZATCA](https://github.com/itsystematic/optima_zatca):** A compliance app for ZATCA regulations in Saudi Arabia.
- **[Optima Payment](https://github.com/itsystematic/optima_payment):** Simplify ERPNext payments with PDC, company expenses, and LC management.
- **[ERPNext Themes](https://github.com/itsystematic/themes):** beautifully designed ERPNext with stunning color themes, Arabic Almarai font, and Arabic human translations.
