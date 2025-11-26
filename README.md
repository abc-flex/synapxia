# SinapxIA Dashboard

**System for Insight, Adoption, Practice & eXpansion through Intelligent Agents**

## Overview

This is a client-side UI demo for the SinapxIA Assignments Dashboard. The application displays employee metrics in a grid format organized by role and team, with interactive avatars that show detailed information.

## Features

- **Dashboard Grid**: Displays employees organized by role (rows) and team (columns)
- **Color-Coded Avatars**: Visual representation of metric levels
  - 🟢 Green: High performance
  - 🟡 Yellow: Medium performance
  - 🔴 Red: Low performance
- **Interactive Modals**: Click on any avatar to view detailed information
- **Dimension Selector**: Switch between different metrics (AI Adoption, Vacation, English Level)
- **Internationalization**: Support for English and Spanish languages
- **Responsive Design**: Works on desktop and mobile devices

## Technology Stack

- **HTML5**: Structure and markup
- **CSS3**: Styling and animations
- **JavaScript (ES6+)**: Client-side logic
- **HTMX**: Progressive enhancement (included but ready for future enhancements)

## Project Structure

```
sinapxia/
├── index.html          # Main HTML structure
├── styles.css          # All styling and layout
├── data.js            # Employee data (JSON format)
├── app.js             # Main application logic
├── i18n.js            # Internationalization support
├── Data.csv           # Original CSV data (reference)
└── README.md          # This file
```

## Getting Started

### Prerequisites

- A modern web browser (Chrome, Firefox, Safari, Edge)
- No server or build tools required - runs entirely client-side

### Installation

1. Clone or download this repository
2. Open `index.html` in your web browser

That's it! The application runs entirely in the browser.

### Usage

1. **View Dashboard**: The main grid shows all employees organized by role and team
2. **Click Avatars**: Click any avatar to see detailed employee information
3. **Edit Metrics**: In the modal, you can change an employee's metric level
4. **Switch Dimensions**: Use the dropdown to switch between different metric dimensions
5. **Change Language**: Use the language selector in the header to switch between English and Spanish

## Data Structure

The application uses a JSON array with the following structure:

```javascript
{
  "name": "Employee Name",
  "email": "email@company.com",
  "role": "BACK|FRONT|QA",
  "team": "HADES|SKYNET|KEPLER|PIXEL|ROCKET",
  "metric": "Alto|Medio|Bajo",
  "date": "DD/MM/YYYY",
  "observation": "Observation text"
}
```

## Customization

### Adding New Dimensions

To add new dimensions, update the dimension selector in `index.html`:

```html
<option value="newDimension">New Dimension</option>
```

### Changing Colors

Modify the avatar colors in `styles.css`:

```css
.avatar.metric-high { background: #34c759; }
.avatar.metric-medium { background: #ffcc00; }
.avatar.metric-low { background: #ff3b30; }
```

### Adding Translations

Add new translations in `i18n.js`:

```javascript
translations.en.newSection = {
  newKey: "Translation"
};
```

## Browser Compatibility

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Future Enhancements

- Backend integration for data persistence
- Advanced filtering and search
- Export functionality (PDF, Excel)
- Historical data tracking
- Analytics dashboard
- User authentication
- Real-time updates

## License

© 2025 SinapxIA. All rights reserved.

## Contact

For questions or support, please contact the development team.
