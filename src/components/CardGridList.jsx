import React from "react";
import { Link, withRouter } from "react-router-dom";
import PropTypes from "prop-types";
import { Card, CardText, CardTitle } from "material-ui/Card";
import RaisedButton from "material-ui/RaisedButton";
import ProgressSpinner from "./ProgressSpinner";
import ErrorCard from "./ErrorCard";
import PaginationBar from "./PaginationBar";
import * as logger from "../services/logger";
import * as searchParams from "../constants/searchParams";

const styles = {
	container: {
		display: "flex",
	},
	cardsContainer: {
		display: "flex",
		flexWrap: "wrap",
		justifyContent: "flex-start",
	},
	buttonContainer: {
		display: "flex",
	},
	button: {
		marginLeft: "5px",
		marginRight: "5px",
	},
	hyperlink: {
		textDecoration: "none",
	},
	card: {
		maxWidth: "300px",
		marginBottom: "20px",
		marginLeft: "20px",
		marginRight: "20px",
	},
	footer: {
		display: "flex",
		justifyContent: "center",
	},
	cardImgContainer: {
		backgroundColor: "black",
		width: "100%",
		height: "300px",
		display: "flex",
		alignItems: "center",
		justifyContent: "center",
	},
	cardImg: {
		display: "block",
		maxWidth: "100%",
		maxHeight: "100%",
	},
};

class CardGridList extends React.PureComponent {
	state = {
		data: undefined,
	};

	_getDataForPage = page => {
		this.props
			.modelApiFn(page)
			.then(response => {
				this.setState({
					currentPage: response.currentPage,
					totalPages: response.totalPages,
					data: response.data,
				});
			})
			.catch(err => {
				logger.error(err);
				this.setState({
					currentPage: null,
					totalPages: null,
					data: null,
				});
			});
	};

	componentDidMount() {
		this._getDataForPage(1);
	}

	componentWillReceiveProps() {
		this.setState({
			data: undefined,
			currentPage: null,
			totalPages: null,
		});
		const qs = new URLSearchParams(location.search);
		const page = qs.get(searchParams.PAGE) ? qs.get(searchParams.PAGE) : 1;
		this._getDataForPage(page);
	}

	_renderControls = () => {
		/* TODO: Add sorting and filtering controls here. */
		return (
			<Card>
				<CardTitle>Sort</CardTitle>
				<div style={styles.buttonContainer}>
					{/* TODO: Support asc / desc */}
					{/* TODO: Register onClick handlers http://www.material-ui.com/#/components/raised-button */}
					<RaisedButton style={styles.button}>Popularity</RaisedButton>
					<RaisedButton style={styles.button}>Title</RaisedButton>
				</div>

				<CardTitle>Filter out</CardTitle>
				{/* TODO: Add text entry and work with query params here */}
			</Card>
		);
	};

	_renderData = () => (
		<div style={styles.container}>
			{this._renderControls()}
			<div>
				<div style={styles.cardsContainer}>
					{this.state.data.map(item => (
						<Link
							key={item.id}
							to={`${this.props.match.url}/${item.id}`}
							style={styles.hyperlink}
						>
							<Card style={styles.card}>
								<div style={styles.cardImgContainer}>
									{<img src={item.imageUrl} style={styles.cardImg} />}
								</div>
								<CardTitle title={item.title} subtitle={item.subtitle} />
								<CardText>
									<ol>
										<li>{item.bonusInfo1}</li>
										<li>{item.bonusInfo2}</li>
										<li>{item.bonusInfo3}</li>
									</ol>
								</CardText>
							</Card>
						</Link>
					))}
				</div>
				<div style={styles.footer}>
					<PaginationBar
						currentPage={this.state.currentPage}
						totalPages={this.state.totalPages}
						location={this.props.history.location}
					/>
				</div>
			</div>
		</div>
	);

	render() {
		if (this.state.data === undefined) {
			return <ProgressSpinner />;
		} else if (this.state.data === null) {
			return <ErrorCard />;
		} else {
			return this._renderData();
		}
	}
}

CardGridList.propTypes = {
	modelApiFn: PropTypes.func.isRequired,
	match: PropTypes.object.isRequired,
	history: PropTypes.object.isRequired,
};

export default withRouter(CardGridList);
