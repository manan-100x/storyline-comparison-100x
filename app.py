from flask import Flask, render_template, request
import numpy as np

app = Flask(__name__)

def calculate_multiple(irr, time):
    # Convert IRR from percentage to decimal
    irr_decimal = irr / 100
    # Calculate multiple using compound interest formula
    multiple = (1 + irr_decimal) ** time
    return round(multiple, 3)

def calculate_irr(multiple, time):
    # Calculate IRR using the nth root formula
    irr_decimal = (multiple ** (1/time)) - 1
    # Convert to percentage
    irr = irr_decimal * 100
    return round(irr, 3)

@app.route('/', methods=['GET', 'POST'])
def index():
    result = None
    calculation_type = None
    
    if request.method == 'POST':
        calculation_type = request.form.get('calculation_type')
        
        if calculation_type == 'multiple':
            irr = float(request.form.get('irr', 0))
            time = float(request.form.get('time', 0))
            result = calculate_multiple(irr, time)
        
        elif calculation_type == 'irr':
            multiple = float(request.form.get('multiple', 0))
            time = float(request.form.get('time', 0))
            result = calculate_irr(multiple, time)
    
    return render_template('index.html', result=result, calculation_type=calculation_type)

if __name__ == '__main__':
    app.run(debug=True) 