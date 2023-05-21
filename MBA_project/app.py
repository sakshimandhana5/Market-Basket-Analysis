from flask import Flask, render_template, request
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from mlxtend.frequent_patterns import apriori, association_rules

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate_rules', methods=['POST'])
def generate_rules():
    # Retrieve data from the uploaded file
    file = request.files['data_file']
    data = pd.read_csv(file)

    #Data_preprocessing
    data['Product Name'] = data['Product Name'].str.strip() #removes spaces from beginning and end
    data.dropna(axis=0, subset=['Invoice No.'], inplace=True) #removes duplicate invoice
    data['Invoice No.'] = data['Invoice No.'].astype('str') #converting invoice number to be string
    data = data[~data['Invoice No.'].str.contains('C')] #remove the credit transactions 

    #grouping invoice no and products
    mybasket = (data.groupby(['Invoice No.', 'Product Name'])['QTY'].sum().unstack().reset_index().fillna(0).set_index('Invoice No.'))
    
    def my_encode_units(x):
       if x <= 0:
           return 0
       if x >= 1:
           return 1

    my_basket_sets = mybasket.applymap(my_encode_units)


    # Run the Apriori algorithm
    my_frequent_itemsets = apriori(my_basket_sets.astype('bool'), min_support=0.002, use_colnames=True)
    my_rules = association_rules(my_frequent_itemsets, metric="lift", min_threshold=1)

    # Generate the sunburst chart
    fig = px.sunburst(my_rules, path=['antecedents','consequents'])#, values='support', color='confidence')
    fig.update_layout(title='Most Associated Products')
     
    # Generate the second bar chart
    itemFrequency = data['Product Name'].value_counts().sort_values(ascending=False)
    fig1 = px.bar(itemFrequency.head(25), title='25 Most Frequent Items', color=itemFrequency.head(25), color_continuous_scale=px.colors.sequential.Magenta)
    fig1.update_layout(margin=dict(t=50, b=0, l=0, r=0), titlefont=dict(size=20), xaxis_tickangle=-45, plot_bgcolor='white', coloraxis_showscale=False)
    fig1.update_yaxes(showticklabels=False, title=' ')
    fig1.update_xaxes(title=' ')
    fig1.update_traces(texttemplate='%{y}', textposition='outside', hovertemplate='<b>%{x}</b><br>No. of Transactions: %{y}')

    # Generate the third bar chart
    mpd = data.groupby('Invoice Date')['Product Name'].count().sort_values(ascending=False)
    fig2 = px.bar(mpd.head(25), title='Most Productive Day', color=mpd.head(25), color_continuous_scale=px.colors.sequential.Mint)
    fig2.update_layout(margin=dict(t=50, b=0, l=0, r=0), titlefont=dict(size=20), xaxis_tickangle=-45, plot_bgcolor='white', coloraxis_showscale=False)
    fig2.update_xaxes(title=' ')
    fig2.update_yaxes(showticklabels=False, title=' ')
    fig2.update_traces(texttemplate='%{y}', textposition='outside', hovertemplate='<b>%{x}</b><br>No. of Transactions: %{y}')

    # Set the chart layout
    fig.update_layout(margin=dict(t=0, l=0, r=0, b=0))

    # Convert my_rules DataFrame to HTML table
    rules_html = my_rules.to_html(classes='table', index=False)

    # Set the chart layout
    fig.update_layout(margin=dict(t=0, l=0, r=0, b=0))

    # Save the chart as HTML
    chart_html = fig.to_html(full_html=False)
    chart_html1 = fig1.to_html(full_html=False)
    chart_html2 = fig2.to_html(full_html=False)

    # Render the results template with the charts
    return render_template('results.html', chart_html=chart_html, chart_html1=chart_html1, chart_html2=chart_html2, rules_html=rules_html)


if __name__ == '__main__':
    app.run(debug=False)