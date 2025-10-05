# Import Streamlit
import streamlit as st

def welcome_page():
    st.title('Welcome to The Ninth Age Data Web App')
    st.markdown("""
    <h3>About This App</h3>
    <p>Whether you\'re looking for ideas for your next army list, want some hard numbers to back up your
        claim that your buddy\'s army is OP, or are just curious
        about the current state of the game, you\'ve come to the right place. Below is an overview of
        the different pages in this app. Below that is a review of some basic statistical concepts
        you may find helpful when interpreting the data.</p>
                
    <p> When you're ready to get started you can use the sidebar on the left to filter the data to your specifications
        and navigate to the different pages of the app.</p>
                
    <h3>Pages</h3>
    <ul>
        <li><b>Welcome</b>: You are here! This page provides an overview of the app and some basic statistical concepts.</li>
        <li><b>Scores & Faction Performance</b>: This page details general statistics about the performance of factions and the distribution
                of scores in the game. It also gives insight into specific matchups between factions;</li>
        <li><b>Faction Popularity</b>: This page presents information about the popularity of factions and 
                the popularity of different pairings in team tournaments.</li>
        <li><b>Magic</b>: This page provides an overview about how much magic lists take, what paths are taken, and how
                these factors affect list performance.</li>
        <li><b>Faction Specific</b>: This page presents more specific insights for each faction; the performance of each category
            (e.g., characters, core, special, etc.) and the popularity and performance of units and unit options are all detailed here.</li>
        <li><b>List Finder</b>: This page allows you to find, and view data on, lists that meet specified criteria. You can filter lists by
            faction, opponent's faction, turn order, units taken, and unit options taken. Once you have made your selections,
            you can view the overall distribution of scores for the lists that meet your criteria, as well as data on each of the
            individual lists. The full roster of units and options for each list is also provided.</li>
        <li><b>Raw Data</b>: This page allows you to view the raw data tables that underpin the analysis shown on the other pages. You
            can even download these tables as .csv files and start performing your own analysis. Please keep in mind that,
            if you haven't applied many filters, these .csv files could be very, very large.</li>
    </ul>
    <h3>Statistical Concepts</h3>
    <ul>
        <li><b>Mean</b>: The average value of a dataset, calculated by summing all values and dividing by the number of values. (Learn more: <a href="https://en.wikipedia.org/wiki/Mean" target="_blank">Wikipedia</a>)</li>
        <li><b>Median</b>: The middle value of a dataset when it is ordered from least to greatest. If there is an even number of values,
            the median is the average of the two middle values. (Learn more: <a href="https://en.wikipedia.org/wiki/Median" target="_blank">Wikipedia</a>)</li>
        <li><b>Standard Deviation</b>: A measure of how spread out the values in a dataset are. A low standard deviation indicates that the values
            tend to be close to the mean, while a high standard deviation indicates that the values are spread out over a wider range. (Learn more: <a href="https://en.wikipedia.org/wiki/Standard_deviation" target="_blank">Wikipedia</a>)</li>
        <li><b>Standard Error</b>: An estimate of the standard deviation of the mean. It can be a little tricky to understand the difference
            between standard deviation and standard error. The standard deviation describes the variability in the data, while the
            standard error describes the variability in the estimate of the mean. The standard error is always smaller than the standard deviation,
            and it decreases as the sample size increases. (Learn more: <a href="https://en.wikipedia.org/wiki/Standard_error" target="_blank">Wikipedia</a>)</li>
        <li><b>Confidence Interval</b>: A range of values that is likely to contain the true value (e.g., the true mean) with a certain level of confidence.
            Normally, the confidence interval is taken to be two standard errors above and below the mean or is defined to include
            95% of the expected results. Under certain assumptions, these two intervals are about the same. (Learn more: <a href="https://en.wikipedia.org/wiki/Confidence_interval" target="_blank">Wikipedia</a>)</li>
        <li><b>z-score</b>: A measure of how many standard deviations a value is away from the mean. One has to be careful whether
            the z-score is calculated using the standard deviation or the standard error, as this will change its interpretation.
            In this app, z-scores are calculated using the standard error, which means they indicate how many standard errors
            a value is away from the mean. Generally speaking z-scores of less than 2 are not consider significant, while
            z-scores of more than 4 are considered definitely significant. (Learn more: <a href="https://en.wikipedia.org/wiki/Standard_score" target="_blank">Wikipedia</a>)</li>
        <li><b>Null Hypothesis</b>: A default assumption that there is no effect or difference between groups. In statistical testing,
            the null hypothesis is typically tested against an alternative hypothesis that suggests there is an effect or difference.
            In the Ninth Age Data Web App, the null hypothesis is that all factions, units, and options are "balanced", which concretely
            means they should average 10 points a game. (Learn more: <a href="https://en.wikipedia.org/wiki/Null_hypothesis" target="_blank">Wikipedia</a>)</li>
        <li><b>p-value</b>: A measure of the strength of evidence against a null hypothesis. A low p-value (typically < 0.05) indicates that the observed
            data is unlikely to have occurred under the null hypothesis, suggesting that there may be a significant effect or difference present.
            Thus, in our data, a p-value of < 0.05 would suggest that the faction/unit/option in question may not be balanced.
            One has to be very careful when there are a lot of p-values being reported, as some of them are likely to show significance
            (p < 0.05) just by chance. (Learn more: <a href="https://en.wikipedia.org/wiki/P-value" target="_blank">Wikipedia</a>)</li>
    </ul>

    """, unsafe_allow_html=True)