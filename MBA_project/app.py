from flask import Flask, render_template, request
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from mlxtend.frequent_patterns import apriori, association_rules
from plotly.offline import init_notebook_mode, iplot
init_notebook_mode(connected=True)

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate_rules', methods=['POST'])
def generate_rules():
    # Retrieve data from the uploaded file
    file = request.files['data_file']
    data = pd.read_csv(file, encoding='ansi')

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

    modified_rules = my_rules.drop_duplicates(subset=['lift'])
    modified_rules

    # Generate the sunburst chart
    # Generate the sunburst chart
    fig = px.sunburst(modified_rules, path=['antecedents', 'consequents'], labels={'antecedents': 'Antecedents', 'consequents': 'Consequents'})

    # Modify the labels
    fig.update_traces(textinfo='label+percent entry')
    fig.update_layout(title='Most Associated Products')

    # Set custom label formatting function
    def format_label(label):
        if isinstance(label, frozenset):
            label = ', '.join(label)
        return label

    # Convert frozenset objects to strings
    modified_rules['antecedents'] = modified_rules['antecedents']#.apply(lambda x: ", ".join(x))
    modified_rules['consequents'] = modified_rules['consequents']#.apply(lambda x: ", ".join(x))

    # Modify the labels in the DataFrame
    modified_rules['antecedents'] = modified_rules['antecedents'].apply(format_label)
    modified_rules['consequents'] = modified_rules['consequents'].apply(format_label)

    # Update the sunburst chart with modified DataFrame
    fig.data[0].labels = modified_rules['antecedents'].tolist() + modified_rules['consequents'].tolist()

    # Set the chart layout
    fig.update_layout(margin=dict(t=0, l=0, r=0, b=0))
     
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
     

    #Generate the fourth chart
    product_rates = data.groupby('Product Name').sum().reset_index()
    product_rates = product_rates.sort_values('RATE', ascending=False).head(15)  # Sort by RATE and select top 15 products

    # Modify the text attribute to include properly formatted revenue values
    text_labels = product_rates['RATE'][::-1].apply(lambda x: '{:,.0f}'.format(x))

    fig3 = go.Figure(data=go.Scatter(
        x=product_rates['RATE'][::-1],  # Reverse the order of x-axis values
        y=product_rates['Product Name'][::-1],  # Reverse the order of y-axis values
        mode='markers',
        marker=dict(
            color=product_rates['RATE'][::-1],  # Reverse the order of x-axis values
            size=10  # specify size of markers
        ),
        text=text_labels,  # Use the reversed order of text labels
        textposition='middle right',  # Set the position of the labels
    ))

    fig3.update_layout(
        title='Top 15 revenue generated products',
        xaxis=dict(range=[3400, 30000]),
        yaxis=dict(
            categoryorder='array',
            categoryarray=product_rates['Product Name'][::-1]  # Arrange categories based on reversed product names
        ),
        margin=dict(l=100)  # Add space between scatter plot and count numbers
    )

    # Add count labels to the scatter plot
    annotations = [
        dict(
            x=x_val,
            y=y_val,
            text=text_label,
            showarrow=False,
            font=dict(size=10),
            xanchor='left',
            yanchor='middle',
            xshift=10  # Adjust the x-coordinate for spacing
        )
        for x_val, y_val, text_label in zip(product_rates['RATE'][::-1], product_rates['Product Name'][::-1], text_labels)
    ]

    fig3.update_layout(annotations=annotations)

    iplot(fig3)

    
     # Extract and modify the association rules table
    association_df = modified_rules[['antecedents', 'consequents', 'lift']]
    association_df['Item A'] = association_df['antecedents'].str.replace(',', '')
    association_df['Item B'] = association_df['consequents'].str.replace(',', '')
    association_df['Strength Category'] = association_df['lift'].apply(lambda x: 'Strongly associated' if x > 20 else 'Moderately associated' if 10 <= x <= 20 else 'Mildly associated')
    strength_order = ['Strongly associated', 'Moderately associated', 'Mildly associated']
    association_df['Strength Category'] = pd.Categorical(association_df['Strength Category'], categories=strength_order, ordered=True)
    modified_association_df = association_df[['Item A', 'Item B', 'Strength Category']].sort_values('Strength Category')

    # Set the chart layout
    fig.update_layout(margin=dict(t=0, l=0, r=0, b=0))

    # Save the chart as HTML

    chart_html = fig.to_html(full_html=False)
    chart_html1 = fig1.to_html(full_html=False)
    chart_html2 = fig2.to_html(full_html=False)
    chart_html3 = fig3.to_html(full_html=False)
    # Render the results template with the charts
    return render_template('results.html', chart_html=fig.to_html(full_html=False), chart_html1=fig1.to_html(full_html=False), chart_html2=fig2.to_html(full_html=False), chart_html3=fig3.to_html(full_html=False), modified_association_df=modified_association_df.to_html(index=False))


if __name__ == '__main__':
    app.run(debug=False)
